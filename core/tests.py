from django.test import Client, TestCase

from . import logic
from .models import Channel, FridaySession, Post, Punishment, Sentence, Term


class LogicTests(TestCase):
    def test_required_laughs(self):
        self.assertEqual(logic.required_laughs_per_point(0), 1)
        self.assertEqual(logic.required_laughs_per_point(199), 1)
        self.assertEqual(logic.required_laughs_per_point(200), 2)
        self.assertEqual(logic.required_laughs_per_point(499), 2)
        self.assertEqual(logic.required_laughs_per_point(500), 3)
        self.assertEqual(logic.required_laughs_per_point(700), 3)

    def test_fail_points(self):
        self.assertEqual(logic.fail_points(150, 6), 6)   # 1 ос / оп
        self.assertEqual(logic.fail_points(240, 9), 4)   # 2 ос / оп
        self.assertEqual(logic.fail_points(600, 12), 4)  # 3 ос / оп

    def test_flags(self):
        self.assertTrue(logic.needs_extra(100))
        self.assertFalse(logic.needs_extra(200))
        self.assertTrue(logic.needs_split(701))
        self.assertFalse(logic.needs_split(700))

    def test_series_load(self):
        p = Punishment(kind=Punishment.KIND_SERIES, episode_minutes=22)
        self.assertEqual(logic.units_per_op(p), 2)
        p2 = Punishment(kind=Punishment.KIND_SERIES, episode_minutes=45)
        self.assertEqual(logic.units_per_op(p2), 1)

    def test_movie_load(self):
        for minutes, ops in ((59, 1), (60, 1), (61, 2), (120, 2), (121, 3), (240, 3)):
            p = Punishment(kind=Punishment.KIND_MOVIE, duration_minutes=minutes)
            self.assertEqual(logic.movie_fail_points(p), ops, minutes)


class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = __import__("core.models", fromlist=["Member"]).Member.objects.create(name="я", slug="me")
        cls.ch = Channel.objects.create(name="правила", slug="rules", kind=Channel.KIND_RULES)
        cls.post = Post.objects.create(channel=cls.ch, author=cls.me, content="**привет** [[ос]]")
        cls.term = Term.objects.create(short="ос", title="Очко смеха", definition="за смех")
        s = FridaySession.objects.create(tiktoks=150, laughs=6)
        cls.session = s
        p = Punishment.objects.create(title="Тест", kind=Punishment.KIND_MOVIE, duration_minutes=100,
                                      status=Punishment.STATUS_APPROVED)
        cls.pun = p
        cls.sentence = Sentence.objects.create(session=s, punishment=p, spins=1)

    def test_pages(self):
        c = Client()
        for slug in ("rules",):
            r = c.get(f"/c/{slug}/")
            self.assertEqual(r.status_code, 200)
        r = c.get("/c/rules/?partial=1")
        self.assertEqual(r.status_code, 200)
        self.assertIn("привет", r.json()["html"])

    def test_markdown(self):
        html = self.post.content and __import__("core.markdown_lite", fromlist=["render"]).render(self.post.content)
        self.assertIn("<strong>привет</strong>", html)
        self.assertIn('class="term-chip"', html)

    def test_edit_requires_key(self):
        c = Client()
        r = c.post("/api/post/%d/update" % self.post.id, {"content": "x"}, content_type="application/json")
        self.assertEqual(r.status_code, 403)
        r = c.post("/api/auth", {"code": "wrong"}, content_type="application/json")
        self.assertEqual(r.status_code, 403)
        r = c.post("/api/auth", {"code": "friday"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        r = c.post("/api/post/%d/update" % self.post.id, {"content": "новый текст"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, "новый текст")

    def test_award_achievement(self):
        c = Client()
        c.post("/api/auth", {"code": "friday"}, content_type="application/json")
        r = c.post("/api/sentence/%d/update" % self.sentence.id, {"status": "done"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.json().get("achievement"))

    def test_approved_cannot_be_removed(self):
        c = Client()
        c.post("/api/auth", {"code": "friday"}, content_type="application/json")
        r = c.post("/api/punishment/%d/delete" % self.pun.id, {}, content_type="application/json")
        j = r.json()
        self.assertTrue(j.get("archived"))
        self.pun.refresh_from_db()
        self.assertEqual(self.pun.status, Punishment.STATUS_ARCHIVED)
