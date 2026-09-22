from django.contrib import admin

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


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "category", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("channel", "author", "short", "pinned", "updated_at")
    list_filter = ("channel",)

    @admin.display(description="текст")
    def short(self, obj):
        return obj.content[:60]


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("short", "title", "order")


@admin.register(Podsos)
class PodsosAdmin(admin.ModelAdmin):
    list_display = ("title", "active", "order")


@admin.register(Punishment)
class PunishmentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "status", "weight")
    list_filter = ("kind", "status")


class SentenceInline(admin.TabularInline):
    model = Sentence
    extra = 0


@admin.register(FridaySession)
class FridaySessionAdmin(admin.ModelAdmin):
    list_display = ("date", "title", "tiktoks", "laughs")
    inlines = [SentenceInline]


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ("punishment", "session", "spins", "watched_units", "status")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("icon", "title", "punishment", "unlocked_at")
