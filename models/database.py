from sqlalchemy import ( Column, ForeignKey,
    Integer, String,TIMESTAMP, DECIMAL, func, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship

# Database connection setup
Base = declarative_base()

# Database Models
class Medecin(Base):
    __tablename__ = "medecins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Relation avec les patients
    patients = relationship("Patient", back_populates="doctor", cascade="all, delete")

class Patient(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctorid = Column(Integer, ForeignKey('medecins.id', ondelete='CASCADE'), nullable=False)

    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String(10), nullable=False)
    glucose = Column(DECIMAL(5, 2))
    bmi = Column(DECIMAL(5, 2))
    bloodpressure = Column(DECIMAL(5, 2))
    pedigree = Column(DECIMAL(5, 3))
    result = Column(String(50))  # Ajout du champ result
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Contrainte de validation
    __table_args__ = (
        CheckConstraint('age >= 0 AND age <= 150', name='check_age'),
        CheckConstraint("sex IN ('M', 'F', 'Homme', 'Femme')", name='check_sex'),
        CheckConstraint('glucose >= 0', name='check_glucose'),
        CheckConstraint('bmi >= 0 AND bmi <= 100', name='check_bmi'),
        CheckConstraint('pedigree >= 0', name='check_pedigree'),
    )

    # Relations
    doctor = relationship("Medecin", back_populates="patients")
    predictions = relationship("Prediction", back_populates="patient", cascade="all, delete")

class Prediction(Base):
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    patientid = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    result = Column(Integer, nullable=False)  # 0 = non diabétique, 1 = diabétique
    confidence = Column(DECIMAL(5, 2))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # Relation vers le patient associé
    patient = relationship("Patient", back_populates="predictions")