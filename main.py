import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List
import joblib
from starlette.middleware.sessions import SessionMiddleware

from models.database import Base, Medecin, Patient, Prediction  

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Import du modèle
try:
    diabetes_model = joblib.load('model.pkl')
    print("Modèle chargé avec succès")
except Exception as e:
    print(f"Erreur lors du chargement du modèle: {e}")
    diabetes_model = None

# Charger les variables d'environnement
load_dotenv()

# Configuration de la base de données
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

user = os.getenv("PGUSER")
password = os.getenv("PGPASSWORD")
host = os.getenv("PGHOST")
port = os.getenv("PGPORT")
database = os.getenv("PGDATABASE")

# Création de l'engine SQLAlchemy
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}')

# Création de la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Création des tables
Base.metadata.create_all(bind=engine)

# Création de l'application FastAPI
app = FastAPI(
    title="API Gestion Médicale",
    description="API pour la gestion des médecins et patients médicaux",
    version="1.0.0"
)

# Ajout du middleware de session pour utiliser request.session
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# =====================================================
# CONFIGURATION SÉCURITÉ
# =====================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# =====================================================
# FONCTIONS UTILITAIRES
# =====================================================

# get_db : obtient une session de base de données.
def get_db():
    """Obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#verify_doctor_token : décode et valide un token JWT puis récupère un médecin.
async def verify_doctor_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Vérifie le token JWT et retourne l'objet Medecin"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        doctor = get_user_by_username(db, username)
        if not doctor:
            raise HTTPException(status_code=404, detail="Médecin non trouvé")
            
        return doctor
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erreur d'authentification : {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

#verify_password : vérifie un mot de passe avec son hash.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier le mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)

#get_password_hash : fait le hash d’un mot de passe.
def get_password_hash(password: str) -> str:
    """Hasher le mot de passe"""
    return pwd_context.hash(password)

#create_access_token : crée un token JWT encodé.
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

#get_user_by_username : récupère un utilisateur (médecin) par nom d'utilisateur.
def get_user_by_username(db: Session, username: str):
    """Récupérer un utilisateur par nom d'utilisateur"""
    return db.query(Medecin).filter(Medecin.username == username).first()

# get_user_by_email : récupère un utilisateur (médecin) par email.
def get_user_by_email(db: Session, email: str):
    """Récupérer un utilisateur par email"""
    return db.query(Medecin).filter(Medecin.email == email).first()

#authenticate_user : authentifie un utilisateur (utilise get_user_by_username + verify_password).
def authenticate_user(db: Session, username: str, password: str):
    """Authentifier un utilisateur"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

# predict_diabetes : fait une prédiction de diabète à partir des données du patient.
def predict_diabetes(glucose, bloodpressure, bmi, pedigree, age):
    """Faire une prédiction de diabète"""
    if not diabetes_model:
        return None, 0
    
    try:
        # Créer un DataFrame avec les données du patient
        patient_data = pd.DataFrame([[glucose, bloodpressure, bmi, pedigree, age]], 
                                  columns=['Glucose', 'BloodPressure', 'BMI', 'DiabetesPedigreeFunction', 'Age'])
        
        # Faire la prédiction
        prediction = diabetes_model.predict(patient_data)[0]
        prediction_proba = diabetes_model.predict_proba(patient_data)[0]
        
        confidence = max(prediction_proba) * 100
        
        return int(prediction), confidence
        
    except Exception as e:
        print(f"Erreur lors de la prédiction: {e}")
        return None, 0

# =====================================================
# ROUTES D'AUTHENTIFICATION
# =====================================================

# Cette route permet d'afficher la page web de connexion.
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Page de connexion"""
    return templates.TemplateResponse("login.html", {"request": request})

# Cette route traite la soumission du formulaire de connexion.
@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Traitement de la connexion"""
    try:
        user = authenticate_user(db, username, password)
        
        if not user:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Nom d'utilisateur ou mot de passe incorrect"
            })
        
        # Stocker l'ID du médecin dans la session
        request.session["doctor_id"] = user.id
        request.session["username"] = user.username
        
        return RedirectResponse(url="/patients", status_code=303)
        
    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Erreur lors de la connexion: {str(e)}"
        })

# Cette route permet d'afficher la page d'inscription.
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Page d'inscription"""
    return templates.TemplateResponse("register.html", {"request": request})

# Cette route traite la soumission du formulaire d'inscription.
@app.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Traitement de l'inscription"""
    try:
        # Vérifier si l'utilisateur existe déjà
        if get_user_by_username(db, username):
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Ce nom d'utilisateur est déjà pris"
            })
        
        if get_user_by_email(db, email):
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Cette adresse email est déjà utilisée"
            })
        
        # Hasher le mot de passe
        hashed_password = get_password_hash(password)
        
        # Créer le nouvel utilisateur
        new_user = Medecin(
            username=username,
            email=email,
            password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return templates.TemplateResponse("register.html", {
            "request": request,
            "success": "Compte créé avec succès ! Vous pouvez maintenant vous connecter."
        })
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Erreur lors de la création du compte: {str(e)}"
        })

# Cette route permet de se déconnecter.
@app.get("/logout")
async def logout(request: Request):
    """Déconnexion"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# =====================================================
# ROUTES PRINCIPALES
# =====================================================

# Cette route permet d'afficher la page d'accueil.
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Page d'accueil"""
    return templates.TemplateResponse("index.html", {"request": request})

# Cette route permet d'afficher le formulaire d'ajout de patient.
@app.get("/add", response_class=HTMLResponse)
async def show_add_patient_form(request: Request):
    """Afficher le formulaire d'ajout de patient"""
    # Vérifier si l'utilisateur est connecté
    if "doctor_id" not in request.session:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("add_patient.html", {
        "request": request,
        "doctor_id": request.session.get("doctor_id")
    })

# Cette route traite la soumission du formulaire d'ajout de patient.
@app.post("/submit")
async def submit_patient(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    sex: str = Form(...),
    glucose: float = Form(...),
    bmi: float = Form(...),
    bloodpressure: float = Form(...),
    pedigree: float = Form(...),
    db: Session = Depends(get_db)
):
    """Route pour traiter la soumission du formulaire patient"""
    # Vérifier si l'utilisateur est connecté
    if "doctor_id" not in request.session:
        return RedirectResponse(url="/login")
    
    doctor_id = request.session["doctor_id"]
    
    try:
        print(f"Received data: name={name}, age={age}, sex={sex}, glucose={glucose}, bmi={bmi}, bloodpressure={bloodpressure}, pedigree={pedigree}")
        
        # Faire la prédiction
        prediction, confidence = predict_diabetes(glucose, bloodpressure, bmi, pedigree, age)
        print(f"Prediction result: {prediction}, confidence: {confidence}")
        
        # Interpréter le résultat
        if prediction is not None:
            result_text = "Diabétique" if prediction == 1 else "Non diabétique"
        else:
            result_text = "Erreur de prédiction"
            prediction = -1
            confidence = 0
        
        # Créer le nouveau patient
        db_patient = Patient(
            doctorid=doctor_id,
            name=name,
            age=age,
            sex=sex,
            glucose=glucose,
            bmi=bmi,
            bloodpressure=bloodpressure,
            pedigree=pedigree,
            result=result_text
        )
        
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        
        print(f"Patient created with ID: {db_patient.id}")
        
        # Enregistrer la prédiction si elle est valide
        if prediction != -1:
            db_prediction = Prediction(
                patientid=db_patient.id,
                result=int(prediction),
                confidence=float(confidence)
            )
            db.add(db_prediction)
            db.commit()
        
        return RedirectResponse(
            url=f"/patients?success=Patient ajouté avec succès. Résultat: {result_text}",
            status_code=303
        )
        
    except Exception as e:
        db.rollback()
        print(f"Error adding patient: {e}")
        import traceback
        traceback.print_exc()
        
        return templates.TemplateResponse("patient.html", {
            "request": request,
            "error": f"Erreur lors de l'ajout du patient: {str(e)}",
            "doctor_id": doctor_id
        })

# Cette route permet d'afficher le tableau de bord des patients.
@app.get("/patients", response_class=HTMLResponse)
async def patients_dashboard(
    request: Request,
    filter_status: Optional[str] = None,
    sort_by: str = "created_at",
    db: Session = Depends(get_db)
):
    """Tableau de bord des patients"""
    # Vérifier si l'utilisateur est connecté
    if "doctor_id" not in request.session:
        return RedirectResponse(url="/login")
    
    doctor_id = request.session["doctor_id"]
    
    try:
        # Construire la requête de base
        query = db.query(Patient).filter(Patient.doctorid == doctor_id)
        
        # Appliquer le filtre par statut
        if filter_status == "diabetic":
            query = query.filter(Patient.result == "Diabétique")
        elif filter_status == "non_diabetic":
            query = query.filter(Patient.result == "Non diabétique")
        
        # Appliquer le tri
        if sort_by == "name":
            query = query.order_by(Patient.name)
        elif sort_by == "age":
            query = query.order_by(Patient.age.desc())
        elif sort_by == "result":
            query = query.order_by(Patient.result)
        else:
            query = query.order_by(Patient.created_at.desc())
        
        patients = query.all()
        
        # Calculer les statistiques
        total_patients = len(patients)
        diabetic_patients = len([p for p in patients if p.result == "Diabétique"])
        diabetic_percentage = (diabetic_patients / total_patients * 100) if total_patients > 0 else 0
        
        stats = {
            "total": total_patients,
            "diabetic": diabetic_patients,
            "non_diabetic": total_patients - diabetic_patients,
            "diabetic_percentage": round(diabetic_percentage, 1)
        }
        
        return templates.TemplateResponse("patients.html", {
            "request": request,
            "patients": patients,
            "stats": stats,
            "current_filter": filter_status,
            "current_sort": sort_by,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
            "username": request.session.get("username")
        })
        
    except Exception as e:
        return templates.TemplateResponse("patients.html", {
            "request": request,
            "patients": [],
            "stats": {"total": 0, "diabetic": 0, "non_diabetic": 0, "diabetic_percentage": 0},
            "error": f"Erreur lors de la récupération des données: {str(e)}",
            "username": request.session.get("username")
        })

# Cette route permet de supprimer un patient.
@app.post("/delete/{patient_id}")
async def delete_patient(patient_id: int, request: Request, db: Session = Depends(get_db)):
    """Supprimer un patient"""
    # Vérifier si l'utilisateur est connecté
    if "doctor_id" not in request.session:
        return RedirectResponse(url="/login")
    
    doctor_id = request.session["doctor_id"]
    
    try:
        # Rechercher le patient
        patient = db.query(Patient).filter(
            Patient.id == patient_id,
            Patient.doctorid == doctor_id
        ).first()
        
        if not patient:
            return RedirectResponse(
                url="/patients?error=Patient non trouvé",
                status_code=303
            )
        
        # Supprimer le patient (les prédictions seront supprimées automatiquement grâce au cascade)
        db.delete(patient)
        db.commit()
        
        return RedirectResponse(
            url="/patients?success=Patient supprimé avec succès",
            status_code=303
        )
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url=f"/patients?error=Erreur lors de la suppression: {str(e)}",
            status_code=303
        )


# =====================================================
# ROUTE DE SANTÉ
# =====================================================

# Cette route permet de vérifier l'état de l'API.
@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(),
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

#python -m uvicorn main:app --reload --port 8000