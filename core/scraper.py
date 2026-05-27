import random
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class AmazonSpider:
    """Fetch Amazon product title and main image with Playwright."""

    def __init__(self, headless=False, locale="de-DE"):
        self.headless = headless
        self.locale = locale
        self.playwright = None
        self.browser = None
        self.context = None
        self._start_browser()

    def _start_browser(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context = self.browser.new_context(
            locale=self.locale,
            viewport={"width": 1365, "height": 900},
        )
        print("Playwright Chromium 启动成功")

    def _new_page(self):
        page = self.context.new_page()
        page.set_default_timeout(15000)
        page.route(
            "**/*.{woff,woff2,ttf,otf,css}",
            lambda route: route.abort(),
        )
        return page

    @staticmethod
    def _clean_text(value):
        return value.strip() if value else ""

    def fetch_product_data(self, url):
        """抓取商品标题和主图链接。"""
        page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.mouse.wheel(0, random.randint(250, 700))
            time.sleep(random.uniform(1.5, 3.0))

            title = self._get_title(page)
            image_url = self._get_image_url(page)

            if not title:
                raise ValueError("未找到商品标题")

            return {"title": title, "image_url": image_url or "无图片"}
        except Exception as exc:
            print(f"抓取异常: {exc}")
            return {"title": "抓取失败", "image_url": "抓取失败"}
        finally:
            page.close()

    def _get_title(self, page):
        selectors = [
            "#productTitle",
            "#title",
            "span#productTitle",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=15000)
                title = self._clean_text(locator.inner_text())
                if title:
                    return title
            except PlaywrightTimeoutError:
                continue
        return ""

    def _get_image_url(self, page):
        selectors = [
            "#landingImage",
            "#imgBlkFront",
            "#ebooksImgBlkFront",
            "img[data-old-hires]",
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                if locator.count() == 0:
                    continue
                image_url = (
                    locator.get_attribute("src")
                    or locator.get_attribute("data-old-hires")
                    or locator.get_attribute("data-a-dynamic-image")
                )
                if image_url:
                    return image_url
            except Exception:
                continue
        return ""

    def close(self):
        for resource in (self.context, self.browser):
            try:
                if resource:
                    resource.close()
            except Exception:
                pass

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
