from typing import Optional

import sqlmodel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

import reflex as rx
from rxconfig import config


engine = None
SessionLocal = None


def get_async_engine(url: str | None) -> Engine:
    echo_db_query = rx.config.environment.SQLALCHEMY_ECHO.get()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return sqlmodel.create_engine(url, echo=echo_db_query, connect_args=connect_args)


def asession() -> AsyncSession:
    global engine, SessionLocal
    if SessionLocal is None:
        engine = create_async_engine(config.async_db_url)
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
        )
    return SessionLocal()


class Order(rx.Model, table=True):
    name: str
    description: Optional[str] = None
    amount: float


class State(rx.State):
    orders: list[Order] = []

    async def on_load(self):
        async with asession() as session:
            result = await session.exec(Order.select())
            self.orders = result.all()

    async def save_order(self, form_data):
        async with asession() as session:
            order = Order(**form_data)
            session.add(order)
            await session.commit()
            await session.refresh(order)
        self.orders.append(order)

    async def delete_order(self, order_id):
        async with asession() as session:
            order = await session.get(Order, order_id)
            await session.delete(order)
            await session.commit()
        self.orders = [order for order in self.orders if order.id != order_id]


def order_grid():
    return rx.hstack(
        rx.foreach(
            State.orders,
            lambda order: rx.card(
                rx.icon_button(
                    "x",
                    size="1",
                    on_click=State.delete_order(order.id),
                    color_scheme="red",
                    variant="outline",
                    float="right",
                ),
                rx.heading(order.name, size="4"),
                rx.text(
                    rx.cond(order.description, order.description, "No description")
                ),
                rx.text(f"${order.amount}"),
                spacing="3",
            ),
        ),
        wrap="wrap",
    )


def order_form():
    return rx.form(
        rx.data_list.root(
            rx.data_list.item(
                rx.data_list.label("Name"),
                rx.data_list.value(rx.input(name="name")),
            ),
            rx.data_list.item(
                rx.data_list.label("Description"),
                rx.data_list.value(rx.input(name="description")),
            ),
            rx.data_list.item(
                rx.data_list.label("Amount"),
                rx.data_list.value(rx.input(name="amount", type="number")),
            ),
            rx.data_list.item(
                rx.data_list.label(),
                rx.data_list.value(rx.button("Add Order")),
            ),
        ),
        on_submit=State.save_order,
        reset_on_submit=True,
    )


def index() -> rx.Component:
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("Welcome to Async!", size="9"),
            order_grid(),
            rx.separator(),
            order_form(),
        ),
        rx.logo(),
    )


app = rx.App()
app.add_page(index, on_load=State.on_load)
