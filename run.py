"""Windows / LAN entry point using Waitress, never Flask's debug server."""

import logging

from waitress import serve

from app import create_app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    application = create_app()
    port = int(application.config.get('PORT', 8080))
    host = application.config.get('HOST', '0.0.0.0')
    if not 1 <= port <= 65535:
        raise ValueError('PORT 必须为 1–65535 之间的整数。')
    print(f'本机访问：http://127.0.0.1:{port}', flush=True)
    print(f'内网访问：http://本机的内网IPv4地址:{port}', flush=True)
    print('关闭此窗口或按 Ctrl+C 停止网站。', flush=True)
    serve(application, host=host, port=port, threads=8, max_request_body_size=65536)
