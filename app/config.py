import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'txt', 'json'}
    
    # Plugin games configuration
    PLUGIN_GAMES = {
        'mtg': ['simple', 'mtga', 'mtgo', 'archidekt', 'deckstats', 'moxfield', 'scryfall_json'],
        'yugioh': ['ydke', 'ydk'],
        'lorcana': ['dreamborn'],
        'riftbound': ['tts', 'pixelborn', 'piltover_archive'],
        'altered': ['ajordat'],
        'netrunner': ['text', 'bbcode', 'markdown', 'plain_text', 'jinteki'],
        'gundam': ['deckplanet', 'limitless', 'egman', 'exburst'],
        'grand_archive': ['omnideck'],
        'digimon': ['tts', 'digimoncardio', 'digimoncarddev', 'digimoncardapp', 'digimonmeta', 'untap'],
        'one_piece': ['optcgsim', 'egman'],
        'flesh_and_blood': ['fabrary']
    }