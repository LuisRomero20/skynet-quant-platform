import os
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE CONEXIÓN POSTGRESQL
# ==========================================
DB_USER = "postgres"
# Codificamos la contraseña de forma segura para URLs (evita errores de parseo)
DB_PASS = urllib.parse.quote_plus("R0mero$20")  
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "skynet_quant"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Inyectamos el client_encoding para evitar que Windows colapse con caracteres latinos (0xf3)
try:
    engine = create_engine(DATABASE_URL, connect_args={'client_encoding': 'utf8'}, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    Base = declarative_base()
except Exception as e:
    print(f"❌ Error al inicializar el motor SQLAlchemy: {e}")

# ==========================================
# MODELOS DE TABLAS (SCHEMA)
# ==========================================

class Partido(Base):
    __tablename__ = 'partidos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_id = Column(Integer, unique=True, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    torneo = Column(String(100))
    equipo_local = Column(String(100), nullable=False)
    equipo_visitante = Column(String(100), nullable=False)
    goles_local = Column(Integer, nullable=True)
    goles_visitante = Column(Integer, nullable=True)
    estado = Column(String(50))

    estadisticas = relationship("EstadisticaEquipo", back_populates="partido", cascade="all, delete-orphan")

class EstadisticaEquipo(Base):
    __tablename__ = 'estadisticas_equipos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    partido_id = Column(Integer, ForeignKey('partidos.id'), nullable=False)
    equipo = Column(String(100), nullable=False)
    
    corners = Column(Integer, nullable=True)
    tarjetas_amarillas = Column(Integer, nullable=True)
    tarjetas_rojas = Column(Integer, nullable=True)
    tiros_al_arco = Column(Integer, nullable=True)
    posesion_porcentaje = Column(Float, nullable=True)

    partido = relationship("Partido", back_populates="estadisticas")

# ==========================================
# INICIALIZADOR
# ==========================================
def init_db():
    print("🔄 Conectando a PostgreSQL (skynet_quant)...")
    try:
        # Esto forzará la conexión. Si falla, ahora sí veremos el error real.
        Base.metadata.create_all(bind=engine)
        print("✅ Estructura Quant creada exitosamente en PostgreSQL.")
    except BaseException as e:
        # Imprimimos el error crudo ignorando problemas de codificación de consola
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"❌ Error de Conexión a PostgreSQL: {error_msg}")
        print("💡 CHECKLIST DE SOLUCIÓN:")
        print("  1. ¿Creaste la base de datos 'skynet_quant' en pgAdmin?")
        print("  2. ¿El puerto 5432 es el correcto para tu instalación local?")
        print("  3. ¿El servicio de PostgreSQL está en ejecución?")

if __name__ == "__main__":
    init_db()