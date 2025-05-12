import logging
import os
import random
import string
from fastapi import FastAPI, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.future import select
from fastapi.responses import FileResponse
from docx import Document
from docx2pdf import convert
from models import Faculty
from fastapi import APIRouter
from sqlalchemy import extract, func
from datetime import datetime
from database import get_session
from models import Submission

# Настроим логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql+asyncpg://postgres:2gecf232gecf2@localhost:5432/gostdockeasy"

# Создание асинхронного движка базы данных
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Абсолютный путь для временной директории
TEMP_DIR = os.path.join(os.getcwd(), "temp_files")
os.makedirs(TEMP_DIR, exist_ok=True)

# Базовый класс для всех моделей
class Base(DeclarativeBase):
    pass

# Настройки CORS для разрешения всех источников
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Получение сессии
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Создание таблиц при запуске
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Функция для добавления нижнего колонтитула
def add_footer(doc: Document, faculty: str):
    # Добавляем нижний колонтитул
    section = doc.sections[-1]
    footer = section.footer
    paragraph = footer.paragraphs[0]
    
    # Добавляем текст в нижний колонтитул
    run = paragraph.add_run(f"Тестовый нижний колонтитул: {faculty}")
    run.font.size = 120000  # размер шрифта
    
    # Можно настроить расположение, например, выровнять по центру:
    paragraph.alignment = 1  # 0 - влево, 1 - по центру, 2 - вправо

# Функция для генерации уникального имени файла
def generate_unique_filename(extension=".docx"):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + extension

# Функция для заполнения шаблона Word
def fill_template(file_path: str, faculty: str):
    logger.info(f"Файл шаблона: {file_path}")
    # Открываем файл шаблона
    doc = Document(file_path)

    # Заполнение плейсхолдеров
    for paragraph in doc.paragraphs:
        if "{{faculty}}" in paragraph.text:
            paragraph.text = paragraph.text.replace("{{faculty}}", faculty)

    # Добавляем нижний колонтитул
    add_footer(doc, faculty)

    # Генерируем уникальное имя для сохраненного файла
    output_path = os.path.join(TEMP_DIR, generate_unique_filename())
    doc.save(output_path)
    logger.info(f"Сохраненный файл: {output_path}")
    return output_path

@app.post("/submit")
async def submit_file(
    file: UploadFile,
    faculty: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    logger.info(f"Получен файл: {file.filename}")
    
    filename = file.filename.encode('utf-8').decode('utf-8')
    uploaded_file_path = os.path.join(TEMP_DIR, filename)
    
    with open(uploaded_file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    template_path = uploaded_file_path
    logger.info(f"Заполнение шаблона: {template_path}")
    filled_template_path = fill_template(template_path, faculty)
    
    output_pdf_path = os.path.splitext(filled_template_path)[0] + ".pdf"
    logger.info(f"Конвертируем в PDF: {output_pdf_path}")
    convert(filled_template_path, output_pdf_path)

    # Обновляем записи в БД
    async with session.begin():
        # Обновление по факультету
        result = await session.execute(select(Faculty).filter_by(name=faculty))
        faculty_record = result.scalar()

        if faculty_record:
            faculty_record.submissions += 1
        else:
            faculty_record = Faculty(name=faculty, submissions=1)
            session.add(faculty_record)

        # ✅ Добавляем новую запись о подаче
        submission = Submission(faculty_name=faculty)
        session.add(submission)

    logger.info(f"Отправляем PDF: {output_pdf_path}")
    return FileResponse(output_pdf_path, media_type='application/pdf', filename="coursework.pdf")

# Эндпоинт для статистики
@app.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Faculty))
    faculties = result.scalars().all()
    return [{"faculty": f.name, "submissions": f.submissions} for f in faculties]

@app.get("/stats_month")
async def get_monthly_stats(session: AsyncSession = Depends(get_session)):
    current_year = datetime.now().year

    result = await session.execute(
        select(
            extract('month', Submission.created_at).label("month"),
            func.count().label("count")
        )
        .where(extract('year', Submission.created_at) == current_year)
        .group_by("month")
        .order_by("month")
    )

    stats = result.all()

    # Преобразуем цифры месяцев в названия на русском
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]

    response = [
        {
            "date": f"{month_names[int(month)-1]} {current_year}",
            "count": count
        }
        for month, count in stats
    ]

    return response