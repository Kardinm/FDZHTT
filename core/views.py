from __future__ import annotations

import hmac
import json
import random
from collections import defaultdict

from django.conf import settings
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from . import logic, markdown_lite
from .models import (
    Achievement,
    Channel,
    FridaySession,
    Member,
    Podsos,
    Post,
    Punishment,
    Sentence,
    Term,
)

EDIT_COOKIE = "edit_key"


# ------------------------------------------------------------------ helpers


def edit_allowed(request) -> bool:
    got = request.COOKIES.get(EDIT_COOKIE, "")
    return bool(got) and hmac.compare_digest(got, str(settings.EDIT_CODE))


def body_json(request) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def denied() -> JsonResponse:
    return JsonResponse({"ok": False, "error": "Нужен ключ правки (замок слева внизу)."}, status=403)


def channels_by_category():
    grouped: dict[str, list[Channel]] = defaultdict(list)
    for ch in Channel.objects.all():
        grouped[ch.category].append(ch)
    return dict(grouped)


def base_ctx(channel: Channel | None = None) -> dict:
    return {
        "channel": channel,
        "channels_by_category": channels_by_category(),
        "members": Member.objects.all(),
        "terms": Term.objects.all(),
        "edit_allowed": None,  # проставляется в views
    }


def channel_data(channel: Channel) -> dict:
    """Данные под конкретный тип канала."""
    kind = channel.kind
    if kind in (Channel.KIND_RULES, Channel.KIND_CHAT):
        return {"posts": channel.posts.select_related("author")}
    if kind == Channel.KIND_GLOSSARY:
        return {"term_list": Term.objects.all()}
    if kind == Channel.KIND_PUNISHMENTS:
        return {
            "groups": [
                (label, [p for p in Punishment.objects.all() if p.kind == key])
                for key, label in Punishment.KIND_CHOICES
            ]
        }
    if kind == Channel.KIND_WHEEL:
        import json as _json

        pool = Punishment.objects.filter(status=Punishment.STATUS_APPROVED)
        return {
            "wheel_pool": pool,
            "sessions": FridaySession.objects.all(),
            "wheel_json": _json.dumps(
                [
                    {
                        "id": p.id,
                        "title": p.title,
                        "weight": max(1, p.weight),
                        "kind": p.kind,
                        "load_label": p.load_label,
                        "emoji": p.kind_emoji,
                    }
                    for p in pool
                ],
                ensure_ascii=False,
            ),
        }
    if kind == Channel.KIND_PROGRESS:
        return {
            "sessions": FridaySession.objects.prefetch_related(
                "sentences__punishment", "sentences__achievement"
            ),
            "podsos_list": Podsos.objects.filter(active=True),
            "all_puns": Punishment.objects.all(),
            "wheel_url": Channel.objects.filter(kind=Channel.KIND_WHEEL).first(),
        }
    if kind == Channel.KIND_ACHIEVEMENTS:
        return {
            "achievement_list": Achievement.objects.select_related("punishment", "sentence__session"),
            "locked": Punishment.objects.filter(
                status=Punishment.STATUS_APPROVED, achievements__isnull=True
            ),
        }
    if kind == Channel.KIND_SUBSOS:
        return {"podsos_list": Podsos.objects.all()}
    return {}


def render_part(kind: str, ctx: dict) -> str:
    return render_to_string(f"core/parts/{kind}.html", ctx)


def session_payload(s: FridaySession) -> dict:
    return {
        "id": s.id,
        "title": str(s),
        "date": s.date.strftime("%d.%m.%Y"),
        "tiktoks": s.tiktoks,
        "laughs": s.laughs,
        "need": s.required_laughs_per_point,
        "fail_points": s.fail_points,
        "needs_extra": s.needs_extra,
        "needs_split": s.needs_split,
        "extra_podsos": s.extra_podsos_id,
    }


def sentence_payload(x: Sentence) -> dict:
    return {
        "id": x.id,
        "punishment": x.punishment_id,
        "title": str(x.punishment),
        "spins": x.spins,
        "planned": x.planned_units,
        "watched": x.watched_units,
        "unit": x.unit_name,
        "percent": x.progress_percent,
        "status": x.status,
    }


# -------------------------------------------------------------------- views


@ensure_csrf_cookie
def channel_view(request, slug: str):
    channel = get_object_or_404(Channel, slug=slug)
    ctx = base_ctx(channel)
    ctx.update(channel_data(channel))
    ctx["edit_allowed"] = edit_allowed(request)
    ctx["html"] = render_part(channel.kind, ctx)
    ctx["title"] = f"#{channel.name}"
    if request.GET.get("partial"):
        return JsonResponse(
            {
                "ok": True,
                "title": ctx["title"],
                "html": ctx["html"],
                "slug": slug,
                "kind": channel.kind,
                "icon": channel.icon,
                "desc": channel.description,
            }
        )
    return render(request, "core/channel.html", ctx)


def home(request):
    first = Channel.objects.order_by("order", "id").first()
    return redirect("channel", slug=first.slug if first else "rules")


@ensure_csrf_cookie
def terms_json(request):
    data = [
        {"short": t.short, "title": t.title, "definition": t.definition} for t in Term.objects.all()
    ]
    return JsonResponse({"ok": True, "terms": data})


# --------------------------------------------------------------- API: доступ


@require_POST
def api_auth(request):
    data = body_json(request)
    code = str(data.get("code", ""))
    if code and hmac.compare_digest(code, str(settings.EDIT_CODE)):
        resp = JsonResponse({"ok": True})
        resp.set_cookie(EDIT_COOKIE, code, max_age=60 * 60 * 24 * 30, samesite="Lax")
        return resp
    return JsonResponse({"ok": False, "error": "Неверный ключ."}, status=403)


@require_POST
def api_logout(request):
    resp = JsonResponse({"ok": True})
    resp.delete_cookie(EDIT_COOKIE)
    return resp


def guard(request):
    return None if edit_allowed(request) else denied()


# ----------------------------------------------------------------- API: посты


@require_POST
def api_post_create(request):
    if (g := guard(request)) is not None:
        return g
    data = body_json(request)
    channel = get_object_or_404(Channel, slug=data.get("channel", ""))
    author = Member.objects.order_by("order", "id").first()
    post = Post.objects.create(channel=channel, author=author, content=data.get("content", "").strip())
    return JsonResponse(
        {"ok": True, "id": post.id, "html": render_to_string("core/parts/post.html", {"post": post, "edit_allowed": True})}
    )


@require_POST
def api_post_update(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    post = get_object_or_404(Post, pk=pk)
    data = body_json(request)
    post.content = data.get("content", post.content)
    post.save()
    return JsonResponse(
        {
            "ok": True,
            "html": render_to_string("core/parts/post.html", {"post": post, "edit_allowed": True}),
        }
    )


@require_POST
def api_post_delete(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    get_object_or_404(Post, pk=pk).delete()
    return JsonResponse({"ok": True})


# ----------------------------------------------------------------- API: термины


@require_POST
def api_term_create(request):
    if (g := guard(request)) is not None:
        return g
    data = body_json(request)
    term = Term.objects.create(
        short=data.get("short", "").strip(),
        title=data.get("title", "").strip(),
        definition=data.get("definition", "").strip(),
        order=Term.objects.count(),
    )
    return JsonResponse({"ok": True, "id": term.id})


@require_POST
def api_term_update(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    term = get_object_or_404(Term, pk=pk)
    data = body_json(request)
    for field in ("short", "title", "definition"):
        if field in data:
            setattr(term, field, data[field])
    term.save()
    return JsonResponse({"ok": True})


@require_POST
def api_term_delete(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    get_object_or_404(Term, pk=pk).delete()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------- API: подсосы


@require_POST
def api_podsos_create(request):
    if (g := guard(request)) is not None:
        return g
    data = body_json(request)
    p = Podsos.objects.create(
        title=data.get("title", "").strip(),
        description=data.get("description", "").strip(),
        order=Podsos.objects.count(),
    )
    return JsonResponse({"ok": True, "id": p.id})


@require_POST
def api_podsos_update(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    p = get_object_or_404(Podsos, pk=pk)
    data = body_json(request)
    for field in ("title", "description", "active"):
        if field in data:
            setattr(p, field, data[field])
    p.save()
    return JsonResponse({"ok": True})


@require_POST
def api_podsos_delete(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    get_object_or_404(Podsos, pk=pk).delete()
    return JsonResponse({"ok": True})


# ----------------------------------------------------------- API: наказания


def punishment_payload(p: Punishment) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "kind": p.kind,
        "kind_display": p.get_kind_display(),
        "emoji": p.kind_emoji,
        "description": p.description,
        "link": p.link,
        "episode_minutes": p.episode_minutes,
        "duration_minutes": p.duration_minutes,
        "seasons_note": p.seasons_note,
        "status": p.status,
        "weight": p.weight,
        "load_label": p.load_label,
    }


@require_POST
def api_punishment_create(request):
    if (g := guard(request)) is not None:
        return g
    data = body_json(request)
    kind = data.get("kind", Punishment.KIND_SERIES)
    p = Punishment.objects.create(
        title=data.get("title", "").strip(),
        kind=kind,
        description=data.get("description", "").strip(),
        link=data.get("link", "").strip(),
        episode_minutes=data.get("episode_minutes") or None,
        duration_minutes=data.get("duration_minutes") or None,
        seasons_note=data.get("seasons_note", "").strip(),
        status=Punishment.STATUS_PROPOSED,
        weight=2 if kind == Punishment.KIND_VN else 10,
        order=Punishment.objects.count(),
    )
    return JsonResponse({"ok": True, **punishment_payload(p)})


@require_POST
def api_punishment_update(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    p = get_object_or_404(Punishment, pk=pk)
    data = body_json(request)
    num_fields = ("episode_minutes", "duration_minutes", "weight")
    for field in (
        "title",
        "description",
        "link",
        "episode_minutes",
        "duration_minutes",
        "seasons_note",
        "weight",
    ):
        if field in data:
            value = data[field]
            if field in num_fields:
                value = int(value) if value not in (None, "") else (0 if field == "weight" else None)
            setattr(p, field, value)
    # Одобренные наказания нельзя убрать из кола — можно лишь отправить в архив целиком.
    if "status" in data and data["status"] == Punishment.STATUS_APPROVED:
        p.status = Punishment.STATUS_APPROVED
    elif "status" in data and data["status"] == Punishment.STATUS_ARCHIVED and p.status != Punishment.STATUS_APPROVED:
        p.status = Punishment.STATUS_ARCHIVED
    p.save()
    return JsonResponse({"ok": True, **punishment_payload(p)})


@require_POST
def api_punishment_delete(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    p = get_object_or_404(Punishment, pk=pk)
    if p.status == Punishment.STATUS_APPROVED or p.sentences.exists():
        # Правило ООН: добавленное в список наказаний убрать нельзя.
        p.status = Punishment.STATUS_ARCHIVED
        p.save()
        return JsonResponse({"ok": True, "archived": True, "message": "Убрать нельзя — отправлено в архив (правило ООН)."})
    p.delete()
    return JsonResponse({"ok": True})


# --------------------------------------------------------------- API: колесо


@require_POST
def api_spin(request):
    """Весовой выбор наказания (у визуальных новелл — малый шанс)."""
    if (g := guard(request)) is not None:
        return g
    pool = [p for p in Punishment.objects.filter(status=Punishment.STATUS_APPROVED) if p.weight > 0]
    if not pool:
        return JsonResponse({"ok": False, "error": "В колесе пока нет наказаний."}, status=400)
    pick = random.choices(pool, weights=[p.weight for p in pool], k=1)[0]
    return JsonResponse({"ok": True, "punishment": punishment_payload(pick)})


# ------------------------------------------------------------ API: мероприятия


@require_POST
def api_session_create(request):
    if (g := guard(request)) is not None:
        return g
    data = body_json(request)
    from datetime import date as date_cls

    s = FridaySession.objects.create(
        date=data.get("date") or date_cls.today(),
        title=data.get("title", "").strip(),
        tiktoks=int(data.get("tiktoks", 0) or 0),
        laughs=int(data.get("laughs", 0) or 0),
        notes=data.get("notes", "").strip(),
    )
    return JsonResponse({"ok": True, **session_payload(s)})


@require_POST
def api_session_update(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    s = get_object_or_404(FridaySession, pk=pk)
    data = body_json(request)
    if "tiktoks" in data:
        s.tiktoks = max(0, int(data["tiktoks"] or 0))
    if "laughs" in data:
        s.laughs = max(0, int(data["laughs"] or 0))
    if "notes" in data:
        s.notes = data["notes"]
    if "title" in data:
        s.title = data["title"]
    if "extra_podsos" in data:
        s.extra_podsos_id = data["extra_podsos"] or None
    s.save()
    return JsonResponse({"ok": True, **session_payload(s)})


@require_POST
def api_session_delete(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    get_object_or_404(FridaySession, pk=pk).delete()
    return JsonResponse({"ok": True})


# -------------------------------------------------------------- API: отработки


@require_POST
def api_sentence_create(request):
    if (g := guard(request)) is not None:
        return g
    data = body_json(request)
    session = get_object_or_404(FridaySession, pk=data.get("session"))
    punishment = get_object_or_404(Punishment, pk=data.get("punishment"))
    x = Sentence.objects.create(
        session=session,
        punishment=punishment,
        spins=max(1, int(data.get("spins", 1) or 1)),
        note=data.get("note", "").strip(),
    )
    return JsonResponse({"ok": True, **sentence_payload(x)})


@require_POST
def api_sentence_update(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    x = get_object_or_404(Sentence, pk=pk)
    data = body_json(request)
    if "watched_units" in data:
        x.watched_units = max(0, int(data["watched_units"] or 0))
    if "note" in data:
        x.note = data["note"]
    if "status" in data:
        x.status = data["status"]
        if x.status == Sentence.STATUS_DONE:
            from django.utils import timezone

            x.watched_units = max(x.watched_units, x.planned_units)
            x.completed_at = x.completed_at or timezone.now()
        else:
            x.completed_at = None
    x.save()
    ach = logic.award_for_sentence(x)
    return JsonResponse(
        {
            "ok": True,
            **sentence_payload(x),
            "achievement": (
                {"title": ach.title, "icon": ach.icon} if ach else None
            ),
        }
    )


@require_POST
def api_sentence_delete(request, pk: int):
    if (g := guard(request)) is not None:
        return g
    get_object_or_404(Sentence, pk=pk).delete()
    return JsonResponse({"ok": True})
