from aiogram.fsm.state import State, StatesGroup


class PantryFlow(StatesGroup):
    waiting_ingredient_name = State()
    waiting_ingredient_quantity = State()
    waiting_consume_name = State()
    waiting_consume_quantity = State()


class RecipeFlow(StatesGroup):
    waiting_recipe_name = State()
    waiting_recipe_minutes = State()
    waiting_recipe_servings = State()
    waiting_recipe_ingredients = State()
    waiting_recipe_steps = State()
    waiting_recipe_confirm = State()
    waiting_search = State()