"""Расчёты по правилам «политики любительского мазохизма».

Все формулы — из правил:

* количество ос, необходимое для одного оп, зависит от числа тиктоков (т):
    - ``0 т < 1 ос < 200 т``            → 1 ос на 1 оп
    - ``200 т ≤ 2 ос < 500 т``          → 2 ос на 1 оп
    - ``500 т ≤ 3 ос ≤ 700 т``          → 3 ос на 1 оп
* если тиктоков меньше 200 — добавляется ДОПОЛНИТЕЛЬНОЕ сос (одно подсос);
* если тиктоков больше 700 — сборка делится пополам и считается за два мероприятия.
"""
from __future__ import annotations

import math

SPLIT_LIMIT = 700
EXTRA_LIMIT = 200


def required_laughs_per_point(tiktoks: int) -> int:
    """Сколько ос нужно для начисления одного оп."""
    if tiktoks < EXTRA_LIMIT:
        return 1
    if tiktoks < 500:
        return 2
    return 3


def fail_points(tiktoks: int, laughs: int) -> int:
    """Очки проёба (оп) = сколько раз крутить колесо."""
    need = required_laughs_per_point(tiktoks)
    return max(0, laughs) // need


def needs_extra(tiktoks: int) -> bool:
    return tiktoks < EXTRA_LIMIT


def needs_split(tiktoks: int) -> bool:
    return tiktoks > SPLIT_LIMIT


# ---------------------------------------------------------------- выполнение


def units_per_op(punishment) -> int:
    """Серий (единиц) на одно оп для сериалоподобного наказания.

    * ``0 мин < 2 сер ≤ 35 мин``  → 2 серии на оп, если серия ≤ 35 минут;
    * ``35 < 1 сер ≤ 85 мин``     → 1 серия на оп, если серия длиннее 35 минут.
    """
    if punishment.kind != punishment.KIND_SERIES:
        return 1
    ep = punishment.episode_minutes or 0
    return 1 if ep > 35 else 2


def movie_fail_points(punishment) -> int:
    """Сколько оп требует полный просмотр фильма:

    * ``0 ч < 1 оп ≤ 1 ч``; ``1 ч < 2 оп ≤ 2 ч``; ``2 ч < 3 оп ≤ 4 ч``.
    """
    minutes = punishment.duration_minutes or 0
    if minutes <= 60:
        return 1
    if minutes <= 120:
        return 2
    return 3


def planned_units(punishment, spins: int = 1) -> int:
    """Сколько единиц отработки полагается сделать."""
    spins = max(0, spins)
    if punishment.kind == punishment.KIND_VN:
        return 1  # прохождение на одну любую концовку
    if punishment.kind == punishment.KIND_MOVIE:
        return max(1, (punishment.duration_minutes or 0))  # весь метраж в минутах
    return units_per_op(punishment) * spins  # серии


def unit_name(punishment) -> str:
    if punishment.kind == punishment.KIND_MOVIE:
        return "мин"
    if punishment.kind == punishment.KIND_VN:
        return "концовка"
    return "сер."


def load_label(punishment) -> str:
    """Короткое описание нагрузки за одно оп."""
    if punishment.kind == punishment.KIND_VN:
        return "прохождение на одну любую концовку"
    if punishment.kind == punishment.KIND_MOVIE:
        return f"полный метраж · {movie_fail_points(punishment)} оп"
    per = units_per_op(punishment)
    ep = punishment.episode_minutes
    ep_txt = f" · {ep} мин/сер." if ep else ""
    return f"{per} сер. за 1 оп{ep_txt}"


def award_for_sentence(sentence):
    """Создаёт достижение, если наказание достигнуто (и его ещё нет)."""
    from .models import Achievement

    if sentence.status != sentence.STATUS_DONE:
        return None
    if Achievement.objects.filter(sentence=sentence).exists():
        return None
    punishment = sentence.punishment
    icon = {"series": "📺", "movie": "🎬", "vn": "🎮"}.get(punishment.kind, "🏆")
    return Achievement.objects.create(
        title=f"Отработано: {punishment.title}",
        icon=icon,
        description=f"«{punishment}» — наказание достигнуто {sentence.completed_at:%d.%m.%Y}."
        if sentence.completed_at
        else f"«{punishment}» — наказание достигнуто.",
        punishment=punishment,
        sentence=sentence,
    )


__all__ = [
    "required_laughs_per_point",
    "fail_points",
    "needs_extra",
    "needs_split",
    "units_per_op",
    "movie_fail_points",
    "planned_units",
    "unit_name",
    "load_label",
    "award_for_sentence",
]
