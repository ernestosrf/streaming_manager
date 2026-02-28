import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.content import StreamingPlatform, db

def init_streaming_platforms():
    """Inicializa as plataformas de streaming brasileiras"""
    
    platforms = [
        {
            'name': 'Netflix',
            'color': '#E50914',
            'logo_url': 'https://logos-world.net/wp-content/uploads/2020/04/Netflix-Logo.png'
        },
        {
            'name': 'Disney+',
            'color': '#113CCF',
            'logo_url': 'https://logos-world.net/wp-content/uploads/2022/01/Disney-Plus-Logo.png'
        },
        {
            'name': 'Max',
            'color': '#7B2CBF',
            'logo_url': 'https://logos-world.net/wp-content/uploads/2023/04/Max-Logo.png'
        },
        {
            'name': 'Amazon Prime Video',
            'color': '#00A8E1',
            'logo_url': 'https://logos-world.net/wp-content/uploads/2021/02/Amazon-Prime-Video-Logo.png'
        },
        {
            'name': 'Pirataria',
            'color': '#000000',
            'logo_url': 'https://cdn-icons-png.flaticon.com/512/1144/1144760.png'
        },
        {
            'name': 'Crunchyroll',
            'color': '#FF6600',
            'logo_url': 'https://logos-world.net/wp-content/uploads/2021/03/Crunchyroll-Logo.png'
        },
        {
            'name': 'Paramount+',
            'color': '#0064FF',
            'logo_url': 'https://logos-world.net/wp-content/uploads/2021/03/Paramount-Plus-Logo.png'
        },
        {
            'name': 'Mercado Play',
            'color': '#FFE600',
            'logo_url': 'https://logodownload.org/wp-content/uploads/2018/10/mercado-livre-logo.png'
        }
    ]
    
    for platform_data in platforms:
        # Verificar se já existe
        existing = StreamingPlatform.query.filter_by(name=platform_data['name']).first()
        if not existing:
            platform = StreamingPlatform(**platform_data)
            db.session.add(platform)
    
    db.session.commit()
    print(f"Inicializadas {len(platforms)} plataformas de streaming")

if __name__ == '__main__':
    from main import app
    with app.app_context():
        init_streaming_platforms()

