from sqlalchemy import Column, INT, BIGINT, TIMESTAMP, func, VARCHAR, UniqueConstraint, ForeignKey
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(BIGINT, primary_key=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("owner_id", "english"),
    )

    word_id = Column(INT, primary_key=True)
    english = Column(VARCHAR(length=50), nullable=False)
    russian = Column(VARCHAR(length=50), nullable=False)
    owner_id = Column(BIGINT)
    created_at = Column(TIMESTAMP, server_default=func.now())


class UserActiveWord(Base):
    __tablename__ = "user_active_words"

    user_id = Column(BIGINT, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    word_id = Column(INT, ForeignKey("words.word_id", ondelete="CASCADE"), primary_key=True)
    added_at =  Column(TIMESTAMP, server_default=func.now())

    user = relationship(User, backref="active_word")
    word = relationship(Word, backref="active_word")


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
