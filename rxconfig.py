"""Reflex 專案設定。

只負責 Reflex framework 層級的設定（port / 模組進入點）。
應用層的設定（DATA_MODE 等）一律放在 app/config.py。
"""

import reflex as rx

config = rx.Config(
    app_name="app",
    app_module_import="app.main",
    frontend_port=3000,
    backend_port=8000,
    telemetry_enabled=False,
    show_built_with_reflex=False,
    plugins=[
        # Reflex 0.9 起 Radix 主題改由 plugin 設定，不再放在 rx.App(theme=...)。
        # 顏色 / 圓角等細節仍以 app/theme.py 的 token 為準，這裡只設定基底。
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                has_background=True,
                accent_color="blue",
                gray_color="slate",
                radius="medium",
                scaling="100%",
            ),
        ),
    ],
    # 內部工具不需要 sitemap，關掉以免每次啟動出現預設插件提示。
    disable_plugins=[rx.plugins.SitemapPlugin],
)
