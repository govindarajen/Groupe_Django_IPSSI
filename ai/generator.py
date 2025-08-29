import os, io, json, random, base64, time, logging
from typing import Dict, Any, List, Optional
import requests
from PIL import Image

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HF_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")
# Modèles avec fallback - par ordre de préférence
TEXT_MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.2",  # Version instruct plus récente
    "mistralai/Mistral-7B-v0.1",
    "HuggingFaceH4/zephyr-7b-beta", 
    "google/flan-t5-xxl",  # Version plus grande de FLAN-T5
]
IMG_MODEL = os.environ.get("HF_IMG_MODEL", "stabilityai/stable-diffusion-2-1")

API_BASE = "https://api-inference.huggingface.co/models"

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

def _hf_post(model: str, payload: Dict[str, Any], stream: bool = False, max_retries: int = 3):
    """Fonction robuste pour interagir avec l'API Hugging Face"""
    url = f"{API_BASE}/{model}"
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Tentative {attempt+1} avec le modèle: {model}")
            resp = requests.post(url, headers=HEADERS, json=payload, stream=stream, timeout=120)
            
            # Gestion des erreurs spécifiques
            if resp.status_code == 404:
                logger.error(f"Modèle {model} non trouvé (404)")
                raise Exception(f"Modèle {model} non trouvé. Essayez un autre modèle.")
            elif resp.status_code == 503:
                # Modèle en cours de chargement
                try:
                    error_data = resp.json()
                    wait_time = error_data.get("estimated_time", 30)
                    logger.info(f"Modèle en cours de chargement, attente de {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                except:
                    time.sleep(30)
                    continue
            elif resp.status_code == 429:
                # Trop de requêtes
                wait_time = 60
                logger.warning(f"Rate limit atteint, attente de {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif resp.status_code != 200:
                logger.error(f"Erreur HTTP {resp.status_code}: {resp.text}")
                resp.raise_for_status()
                
            return resp
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Erreur de connexion, nouvelle tentative dans 10s...")
            time.sleep(10)
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout, nouvelle tentative dans 15s...")
            time.sleep(15)
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Échec après {max_retries} tentatives: {e}")
                raise
            wait_time = (attempt + 1) * 10
            logger.warning(f"Erreur de requête, nouvelle tentative dans {wait_time}s...")
            time.sleep(wait_time)
    
    raise Exception(f"Échec après {max_retries} tentatives avec le modèle {model}")

def generate_with_fallback(prompt: str, max_tokens: int = 800) -> str:
    """Tente de générer du texte avec plusieurs modèles en cascade"""
    for model in TEXT_MODELS:
        try:
            payload = {
                "inputs": prompt.strip(),
                "parameters": {
                    "max_new_tokens": max_tokens, 
                    "temperature": 0.7, 
                    "return_full_text": False,
                    "do_sample": True,
                    "top_p": 0.9
                },
                "options": {"wait_for_model": True},
            }
            
            resp = _hf_post(model, payload)
            data = resp.json()
            
            # Extraction du texte généré selon différents formats de réponse
            if isinstance(data, list) and data:
                if isinstance(data[0], dict) and "generated_text" in data[0]:
                    return data[0]["generated_text"]
                else:
                    return str(data[0])
            elif isinstance(data, dict):
                if "generated_text" in data:
                    return data["generated_text"]
                elif "text" in data:
                    return data["text"]
                elif "generated_texts" in data and data["generated_texts"]:
                    return data["generated_texts"][0]
                else:
                    # Tentative d'extraire n'importe quelle valeur texte
                    for key, value in data.items():
                        if isinstance(value, str) and len(value) > 20:
                            return value
                    return str(data)
            else:
                return str(data)
                
        except Exception as e:
            logger.error(f"Échec avec {model}: {e}")
            continue
    
    # Fallback manuel si tous les modèles échouent
    logger.error("Tous les modèles ont échoué, utilisation du fallback manuel")
    return fallback_manual_response()

def fallback_manual_response() -> str:
    """Génère une réponse manuelle si tous les modèles échouent"""
    return json.dumps({
        "universe": "Un univers fantastique où la magie et la technologie coexistent.",
        "scenario": {
            "act1": "Le héros découvre ses pouvoirs et se lance dans l'aventure.",
            "act2": "Affrontement avec les forces antagonistes et découvertes de trahisons.",
            "act3": "Résolution finale et confrontation avec le grand méchant."
        },
        "twist": "Le mentor du héros est en réalité le véritable antagoniste.",
        "characters": [
            {
                "name": "Aelryn",
                "class": "Mage",
                "role": "Protagoniste",
                "background": "Jeune apprenti découvrant ses pouvoirs exceptionnels",
                "gameplay": "Magie offensive et défensive avec invocations"
            },
            {
                "name": "Kaelen",
                "class": "Guerrier",
                "role": "Compagnon",
                "background": "Soldat vétéran cherchant la rédemption",
                "gameplay": "Combat au corps à corps avec différentes armes"
            }
        ],
        "locations": [
            {
                "name": "Cité Céleste",
                "description": "Une ville flottante où la magie est source d'énergie"
            },
            {
                "name": "Forêt des Anciens",
                "description": "Une forêt primitive habitée par des créatures mystiques"
            }
        ],
        "pitch": "Plongez dans une aventure épique où vos choix façonnent le destin du monde. Une expérience de jeu unique mêlant exploration, combat tactique et narration riche."
    }, ensure_ascii=False)

# --------- Génération TEXTE ---------
def generate_structured_game(title: str, genre: str, ambiance: str, keywords: str, references: str) -> Dict[str, Any]:
    prompt = f"""
Tu es un assistant de Game Design. Génère STRICTEMENT un JSON valide en français décrivant un concept de jeu vidéo.

Champs EXACTS attendus :
- "universe": description courte (3-5 lignes)
- "scenario": objet avec "act1", "act2", "act3" (2-4 lignes chacun)
- "twist": une phrase
- "characters": liste 2 à 4 personnages {{"name","class","role","background","gameplay"}}
- "locations": liste 2 à 3 lieux {{"name","description"}}
- "pitch": 2-3 phrases marketing

Contraintes : Pas de texte hors JSON. Pas de markdown. Pas de commentaires.

Contexte:
titre="{title}"
genre="{genre}"
ambiance="{ambiance}"
mots_cles="{keywords}"
references="{references}"
"""

    try:
        text = generate_with_fallback(prompt)
        
        # Nettoyage et extraction du JSON
        text = text.strip().strip("`")  # Retirer les backticks Markdown
        
        # Chercher un bloc JSON
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx+1]
        else:
            json_str = text
            
        # Essayer de parser le JSON
        try:
            parsed = json.loads(json_str)
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Erreur de parsing JSON: {e}, texte reçu: {text}")
            # Si le parsing échoue, retourner une structure de base avec le texte brut
            return {
                "universe": "Univers généré par IA",
                "scenario": {
                    "act1": "Premier acte du scénario",
                    "act2": "Deuxième acte du scénario", 
                    "act3": "Troisième acte du scénario"
                },
                "twist": "Une twist narrative intéressante",
                "characters": [
                    {
                        "name": "Personnage Principal",
                        "class": "Classe par défaut",
                        "role": "Rôle dans l'histoire",
                        "background": "Histoire du personnage",
                        "gameplay": "Style de gameplay"
                    }
                ],
                "locations": [
                    {
                        "name": "Lieu emblématique",
                        "description": "Description du lieu"
                    }
                ],
                "pitch": "Un jeu passionnant qui va révolutionner le genre",
                "raw_text": text  # Inclure le texte original pour débogage
            }
            
    except Exception as e:
        logger.error(f"Erreur critique dans generate_structured_game: {e}")
        # Fallback ultime en cas d'échec complet
        return fallback_manual_response()

# --------- Génération IMAGE ---------
def generate_concept_image(prompt: str) -> Image.Image:
    """
    Retourne une PIL.Image à partir d'un prompt. Gère image/png ou base64.
    """
    try:
        payload = {"inputs": prompt, "options": {"wait_for_model": True}}
        resp = _hf_post(IMG_MODEL, payload, stream=True)
        ctype = resp.headers.get("content-type", "")

        # Cas 1 : image binaire directe
        if "image/" in ctype:
            content = resp.content
            return Image.open(io.BytesIO(content)).convert("RGB")

        # Cas 2 : JSON contenant du base64
        try:
            data = resp.json()
            for k in ("image", "generated_image", "images"):
                if k in data:
                    if isinstance(data[k], list) and data[k]:
                        b64 = data[k][0]
                    else:
                        b64 = data[k]
                    raw = base64.b64decode(b64)
                    return Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception as e:
            logger.error(f"Erreur de décodage image: {e}")
            pass

        raise RuntimeError(f"Réponse image inattendue (content-type: {ctype})")
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'image: {e}")
        # Retourner une image de fallback
        return Image.new('RGB', (512, 512), color=(73, 109, 137))

# --------- Exploration libre ---------
def random_seed_game() -> Dict[str, str]:
    genres = ["RPG", "FPS", "Metroidvania", "Visual Novel", "Rogue-lite", "Tactique"]
    ambs = ["cyberpunk", "dark fantasy", "onirique", "post-apo", "low-poly coloré"]
    keys = ["boucle temporelle", "IA rebelle", "vengeance", "mémoire fragmentée", "multivers"]
    refs = ["Zelda", "Hollow Knight", "Disco Elysium", "Hades", "Celeste"]

    return {
        "title": f"Proto-{random.randint(1000,9999)}",
        "genre": random.choice(genres),
        "ambiance": random.choice(ambs),
        "keywords": ", ".join(random.sample(keys, 2)),
        "references": random.choice(refs),
    }