"""
Main entry point cho RESTful API server
"""
import asyncio
import sys
import argparse
from pathlib import Path
from backend.rest_api import RESTAPIServer

def main():
    parser = argparse.ArgumentParser(description='RESTful API Chat Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host address (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Port (default: 8000)')
    parser.add_argument('--ssl-cert', default='server.crt', help='SSL certificate file (default: server.crt)')
    parser.add_argument('--ssl-key', default='server.key', help='SSL key file (default: server.key)')
    parser.add_argument('--no-ssl', action='store_true', help='Chạy server không SSL')
    
    args = parser.parse_args()
    
    # Kiểm tra SSL files
    ssl_cert = None
    ssl_key = None
    
    if not args.no_ssl:
        if Path(args.ssl_cert).exists() and Path(args.ssl_key).exists():
            ssl_cert = args.ssl_cert
            ssl_key = args.ssl_key
            print(f"Sử dụng SSL certificate: {ssl_cert}")
        else:
            print(f"Warning: SSL certificate không tìm thấy. Chạy server không SSL.")
            print(f"Để tạo SSL certificate, chạy: python backend/generate_ssl_cert.py")
    
    # Tạo và khởi động server
    server = RESTAPIServer(
        host=args.host,
        port=args.port,
        ssl_cert=ssl_cert,
        ssl_key=ssl_key
    )
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nĐang dừng server...")
        sys.exit(0)

if __name__ == "__main__":
    main()

