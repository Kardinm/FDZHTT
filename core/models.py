from __future__ import annotations

from datetime import date

from django.db import models
from django.urls import reverse

from . import logic


class Member(models.Model):
    """Участник пространства (отображается в правой колонке, как в Discord)."""

    name = models.CharField("имя", max_length=64)
    slug = models.SlugField("слаг", unique=True)
    emoji = models.CharField("эмодзи-аватар", max_length=8, default="🙂")
    color = models.CharField("цвет", max_length=7, default="#5865f2")
    status = models.CharField("статус", max_length=128, blank=True, default="")
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "участник"
        verbose_name_plural = "участники"

    def __str__(self) -> str:
        return self.name


class Channel(models.Model):
    """Раздел сайта = канал в Discord."""

    KIND_RULES = "rules"
    KIND_CHAT = "chat"
    KIND_GLOSSARY = "glossary"
    KIND_PUNISHMENTS = "punishments"
    KIND_WHEEL = "wheel"
    KIND_PROGRESS = "progress"
    KIND_ACHIEVEMENTS = "achievements"
    KIND_SUBSOS = "subsos"
    KIND_CHOICES = [
        (KIND_RULES, "Правила (сообщения)"),
        (KIND_CHAT, "Чат (сообщения)"),
        (KIND_GLOSSARY, "Определения"),
        (KIND_PUNISHMENTS, "Список наказаний"),
        (KIND_WHEEL, "Колесо"),
        (KIND_PROGRESS, "Прогресс"),
        (KIND_ACHIEVEMENTS, "Достижения"),
        (KIND_SUBSOS, "Подсосы"),
    ]

    name = models.CharField("название", max_length=64)
    slug = models.SlugField("слаг", unique=True)
    kind = models.CharField("тип", max_length=16, choices=KIND_CHOICES, default=KIND_CHAT)
    icon = models.CharField("иконка", max_length=8, default="#")
    category = models.CharField("категория", max_length=64, default="ПРОЧЕЕ")
    description = models.CharField("описание", max_length=200, blank=True, default="")
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "канал"
        verbose_name_plural = "каналы"

    def __str__(self) -> str:
        return f"#{self.name}"

    def get_absolute_url(self) -> str:
        return reverse("channel", args=[self.slug])


class Post(models.Model):
    """Сообщение в канале-чате (правила, обсуждения)."""

    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="posts", verbose_name="канал"
    )
    author = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="автор",
    )
    content = models.TextField("содержимое", blank=True, default="")
    pinned = models.BooleanField("закреплено", default=False)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "сообщение"
        verbose_name_plural = "сообщения"

    def __str__(self) -> str:
        return f"{self.channel} · {self.content[:32]}"


class Term(models.Model):
    """Термин из списка определений."""

    short = models.CharField("короткое имя (напр. «ос»)", max_length=32, unique=True)
    title = models.CharField("полное название", max_length=200)
    definition = models.TextField("определение", blank=True, default="")
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "термин"
        verbose_name_plural = "термины"

    def __str__(self) -> str:
        return self.short


class Podsos(models.Model):
    """Подсос — вариант для ДОПОЛНИТЕЛЬНОГО сос."""

    title = models.CharField("название", max_length=120)
    description = models.TextField("описание", blank=True, default="")
    active = models.BooleanField("доступен для выбора", default=True)
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "подсос"
        verbose_name_plural = "подсосы"

    def __str__(self) -> str:
        return self.title


class Punishment(models.Model):
    """Наказание из списка кола. Одобренные убрать нельзя (см. ООН)."""

    KIND_SERIES = "series"
    KIND_MOVIE = "movie"
    KIND_VN = "vn"
    KIND_CHOICES = [
        (KIND_SERIES, "Сериал / аниме / дорама / мультсериал"),
        (KIND_MOVIE, "Фильм / мультфильм"),
        (KIND_VN, "Визуальная новелла"),
    ]
    STATUS_PROPOSED = "proposed"
    STATUS_APPROVED = "approved"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_PROPOSED, "Предложено"),
        (STATUS_APPROVED, "В колесе"),
        (STATUS_ARCHIVED, "В архиве"),
    ]

    title = models.CharField("название", max_length=200)
    kind = models.CharField("тип", max_length=10, choices=KIND_CHOICES, default=KIND_SERIES)
    description = models.TextField("описание", blank=True, default="")
    link = models.URLField("ссылка", blank=True, default="")
    # Для сериалов: длительность одной серии в минутах.
    episode_minutes = models.PositiveIntegerField("минут в серии", blank=True, null=True)
    # Для фильмов: полный метраж в минутах.
    duration_minutes = models.PositiveIntegerField("длительность, мин", blank=True, null=True)
    seasons_note = models.CharField(
        "заметка о сезонах", max_length=200, blank=True, default=""
    )
    status = models.CharField(
        "статус", max_length=10, choices=STATUS_CHOICES, default=STATUS_PROPOSED
    )
    weight = models.PositiveIntegerField(
        "вес в колесе", default=10, help_text="Чем меньше, тем реже выпадает (у ВН — малый шанс)."
    )
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "наказание"
        verbose_name_plural = "наказания"

    def __str__(self) -> str:
        return self.title

    @property
    def kind_emoji(self) -> str:
        return {"series": "📺", "movie": "🎬", "vn": "🎮"}.get(self.kind, "💀")

    @property
    def load_label(self) -> str:
        """Человекочитаемая «нагрузка за одно оп»."""
        return logic.load_label(self)

    @property
    def units_per_op(self) -> int:
        """Сколько единиц отработки (серий / прочее) приходится на одно оп."""
        return logic.units_per_op(self)


class FridaySession(models.Model):
    """Мероприятие «политики любительского мазохизма» (обычно — пятница)."""

    date = models.DateField("дата", default=date.today)
    title = models.CharField("название", max_length=120, blank=True, default="")
    tiktoks = models.PositiveIntegerField("тиктоков в сборке (т)", default=0)
    laughs = models.PositiveIntegerField("очки смеха (ос)", default=0)
    extra_podsos = models.ForeignKey(
        Podsos,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="выбранный подсос",
    )
    notes = models.TextField("заметки", blank=True, default="")
    held = models.BooleanField("мероприятие проведено", default=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "мероприятие"
        verbose_name_plural = "мероприятия"

    def __str__(self) -> str:
        return self.title or f"ПЛМ от {self.date:%d.%m.%Y}"

    # ---- расчёты по правилам ----

    @property
    def required_laughs_per_point(self) -> int:
        """Сколько ос нужно для начисления одного оп (зависит от количества т)."""
        return logic.required_laughs_per_point(self.tiktoks)

    @property
    def fail_points(self) -> int:
        """Очки проёба (оп) = сколько раз крутить колесо."""
        return logic.fail_points(self.tiktoks, self.laughs)

    @property
    def needs_extra(self) -> bool:
        """< 200 т → добавляется ДОПОЛНИТЕЛЬНОЕ сос."""
        return logic.needs_extra(self.tiktoks)

    @property
    def needs_split(self) -> bool:
        """> 700 т → сборку надо делить пополам на два мероприятия."""
        return logic.needs_split(self.tiktoks)


class Sentence(models.Model):
    """Отработка одного «кола»: конкретное наказание из колеса."""

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "progress"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_PENDING, "В очереди"),
        (STATUS_IN_PROGRESS, "В процессе"),
        (STATUS_DONE, "Отработано"),
    ]

    session = models.ForeignKey(
        FridaySession,
        on_delete=models.CASCADE,
        related_name="sentences",
        verbose_name="мероприятие",
    )
    punishment = models.ForeignKey(
        Punishment, on_delete=models.PROTECT, related_name="sentences", verbose_name="наказание"
    )
    spins = models.PositiveIntegerField("колов (оп)", default=1)
    watched_units = models.PositiveIntegerField("просмотрено единиц", default=0)
    note = models.CharField("заметка", max_length=200, blank=True, default="")
    status = models.CharField("статус", max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    completed_at = models.DateTimeField("отработано", null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "отработка"
        verbose_name_plural = "отработки"

    def __str__(self) -> str:
        return f"{self.punishment} × {self.spins}"

    @property
    def unit_name(self) -> str:
        return logic.unit_name(self.punishment)

    @property
    def planned_units(self) -> int:
        """Сколько единиц надо отсмотреть/пройти по правилам выполнения."""
        return logic.planned_units(self.punishment, self.spins)

    @property
    def progress_percent(self) -> int:
        planned = self.planned_units
        if planned <= 0:
            return 100 if self.status == self.STATUS_DONE else 0
        return min(100, round(self.watched_units * 100 / planned))


class Achievement(models.Model):
    """Достижение — выдаётся, когда наказание достигнуто (отработано)."""

    title = models.CharField("название", max_length=200)
    icon = models.CharField("иконка", max_length=8, default="🏆")
    description = models.TextField("описание", blank=True, default="")
    punishment = models.ForeignKey(
        Punishment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="achievements",
        verbose_name="наказание",
    )
    sentence = models.OneToOneField(
        Sentence,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="achievement",
        verbose_name="отработка",
    )
    unlocked_at = models.DateTimeField("получено", auto_now_add=True)

    class Meta:
        ordering = ["-unlocked_at", "-id"]
        verbose_name = "достижение"
        verbose_name_plural = "достижения"

    def __str__(self) -> str:
        return f"{self.icon} {self.title}"
