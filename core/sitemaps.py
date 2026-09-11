from wagtail.contrib.sitemaps import Sitemap


class TranslatedSitemap(Sitemap):
    """Wagtail's sitemap lists the site root's descendants. Each translation of the home page is a separate
    root, so translated pages would be missing. Include every locale's tree for this site."""

    def items(self):
        site = self.get_wagtail_site()
        pages = None
        for root in site.root_page.get_translations(inclusive=True):
            tree = root.get_descendants(inclusive=True).live().public()
            pages = tree if pages is None else pages | tree
        return pages.order_by("path").defer_streamfields().specific()
