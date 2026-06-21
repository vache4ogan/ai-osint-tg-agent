
from html import entities

from sqlalchemy import Nullable, create_engine, Column, Integer, String, ForeignKey, null
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

engine = create_engine("sqlite:///tech_trends.db", echo=False)

Base = declarative_base()


class ArticleEntity(Base):
    __tablename__ = 'article_entities'
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'))
    entity_id = Column(Integer, ForeignKey('entities.id'))


# Table 1 : Papers

class Article(Base):
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)


    entities = relationship("Entity", secondary="article_entities", back_populates="articles")


# Table 2: NER

class Entity(Base):
    __tablename__ = 'entities'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False) # например: "LangChain"
    label = Column(String, nullable=False)             # например: "TECH" или "ORG"
    
    # Обратная связь
    articles = relationship("Article", secondary="article_entities", back_populates="entities")

# Создаем таблицы в файле
Base.metadata.create_all(engine)

# Создаем фабрику сессий (через сессию мы будем сохранять данные)
SessionLocal = sessionmaker(bind=engine)












