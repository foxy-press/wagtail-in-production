import os
import secrets
import subprocess
import sys

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from wagtail.documents.models import Document
from wagtail.images.tests.utils import get_test_image_file

from blog.models import BlogPage
from core.blocks import ImageBlock
from core.testing import SeededSiteTestCase


class DeploySettingsTests(SeededSiteTestCase):
    def test_production_settings_pass_djangos_deploy_checks(self):
        env = {**os.environ, "DEBUG": "0", "SECRET_KEY": secrets.token_urlsafe(50), "ALLOWED_HOSTS": "studio.example"}
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
            env=env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_production_refuses_to_start_without_a_secret_key(self):
        env = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"} | {"DEBUG": "0"}
        result = subprocess.run([sys.executable, "manage.py", "check"], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)


class UploadTests(SeededSiteTestCase):
    """Chapter 14: files editors upload must never run as code in a visitor's browser."""

    def setUp(self):
        self.login()

    def test_html_documents_are_rejected(self):
        upload = SimpleUploadedFile("offer.html", b"<script>alert(1)</script>", content_type="text/html")
        response = self.client.post(reverse("wagtaildocs:add"), {"title": "Offer", "file": upload, "collection": 1})
        self.assertFalse(Document.objects.filter(title="Offer").exists())
        self.assertContains(response, "is not allowed")

    def test_svg_images_are_rejected(self):
        upload = SimpleUploadedFile("logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
        response = self.client.post(reverse("wagtailimages:add"), {"title": "Logo", "file": upload, "collection": 1})
        self.assertContains(response, "Not a supported image format")

    def test_documents_download_rather_than_display(self):
        doc = Document.objects.create(title="Notes", file=ContentFile(b"plain text", name="notes.txt"))
        response = self.client.get(doc.url)
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_admin_is_not_at_the_default_path(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)


class AccessibilityTests(SeededSiteTestCase):
    def test_images_need_alt_text_or_a_decorative_flag(self):
        block = ImageBlock()
        image = get_test_image_file()
        from wagtail.images.models import Image

        picture = Image.objects.create(title="Chart", file=image)
        with self.assertRaises(ValidationError):
            block.clean({"image": picture, "alt": "", "decorative": False, "caption": ""})
        block.clean({"image": picture, "alt": "", "decorative": True, "caption": ""})
        block.clean({"image": picture, "alt": "Bar chart of page speed", "decorative": False, "caption": ""})

    def test_decorative_images_have_empty_alt(self):
        from wagtail.images.models import Image

        picture = Image.objects.create(title="Swirl", file=get_test_image_file())
        post = BlogPage.objects.get(slug="testing-every-live-page")
        post.body = [{"type": "image", "value": {"image": picture.pk, "alt": "", "decorative": True, "caption": ""}}]
        post.save_revision().publish()
        html = self.client.get(post.url).content.decode()
        self.assertIn('alt=""', html)
        self.assertNotIn('alt="Swirl"', html)

    def test_content_checker_covers_main_content_only(self):
        self.login()
        html = self.client.get("/writing/testing-every-live-page/").content.decode()
        self.assertIn("w-userbar", html)
        self.assertRegex(html, r'"include":\s*\["main"\]')
