from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import httpx
import os
from dotenv import load_dotenv
from typing import List, Optional

# Load environment variables from a .env file
load_dotenv()

# Fetch the Dummy JSON API URL from the environment variable
DUMMY_JSON_API_URL = os.getenv("DUMMY_JSON_API_URL", "https://dummyjson.com/products")

# In-memory storage for products
products = []


# Product model for validation
class Product(BaseModel):
    title: str = Field(..., description="Title of the product")
    price: float = Field(..., description="Price of the product")
    category: str = Field(..., description="Category of the product")


# Lifespan function to handle startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global products
    try:
        # Startup: Fetch products from Dummy JSON API
        async with httpx.AsyncClient() as client:
            response = await client.get(DUMMY_JSON_API_URL)
            response.raise_for_status()
            data = response.json()
            products = data.get("products", [])  # Extract product list
            print("Products fetched successfully.")
    except httpx.RequestError as e:
        print(f"Failed to fetch products: {e}")
        products = []  # Set products to empty if fetch fails
    yield
    # Shutdown: Cleanup logic (if needed)
    products.clear()
    print("Products cleared from memory.")


# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)


# GET /products - Fetch all products with pagination and optional title filter
@app.get("/products", response_model=List[Product])
async def get_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, description="Number of items per page"),
    title_startswith: Optional[str] = Query(
        None, description="Filter products by title starting with the specified prefix"
    ),
):
    if not products:
        raise HTTPException(status_code=503, detail="Products data is not available.")

    # Filter products by title if title_startswith is provided
    if title_startswith:
        filtered_products = [
            product
            for product in products
            if product["title"].lower().startswith(title_startswith.lower())
        ]
    else:
        filtered_products = products

    # Pagination logic
    start = (page - 1) * size
    end = start + size
    paginated_products = filtered_products[start:end]

    # Check if page is empty
    if not paginated_products:
        raise HTTPException(
            status_code=404, detail="No products found for the requested page."
        )

    return paginated_products


# POST /products - Add a new product
@app.post("/products", response_model=Product)
async def add_product(new_product: Product):
    product = new_product.model_dump()  # Validate and convert the model to a dict
    products.append(product)
    return product
