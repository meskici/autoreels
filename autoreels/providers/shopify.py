"""Shopify product ingest.

Two paths in:

1. Admin GraphQL API, when SHOPIFY_STORE and SHOPIFY_ADMIN_TOKEN are set.
2. A JSON file (`--product-json`) — which is how you feed it the output of the
   Shopify MCP tools without minting an Admin token.

Both land on the same normalised `Product`.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

from ..http import post_json
from ..models import Image, Product

_PRODUCT_QUERY = """
query ProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    handle
    title
    descriptionHtml
    description
    vendor
    productType
    tags
    onlineStoreUrl
    priceRangeV2 { minVariantPrice { amount currencyCode } }
    media(first: 30) {
      edges { node { ... on MediaImage { image { url altText width height } } } }
    }
  }
}
"""


def fetch(store: str, token: str, handle: str, api_version: str = "2025-01") -> Product:
    """Pull one product by handle from the Admin GraphQL API."""
    if not store or not token:
        raise ValueError(
            "Shopify ingest needs SHOPIFY_STORE and SHOPIFY_ADMIN_TOKEN, "
            "or use --product-json to supply the product directly."
        )
    if not store.endswith(".myshopify.com") and "." not in store:
        store = f"{store}.myshopify.com"

    url = f"https://{store}/admin/api/{api_version}/graphql.json"
    payload = post_json(
        url,
        {"query": _PRODUCT_QUERY, "variables": {"handle": handle}},
        headers={"X-Shopify-Access-Token": token},
    )
    if payload.get("errors"):
        raise RuntimeError(f"Shopify GraphQL errors: {payload['errors']}")
    node = (payload.get("data") or {}).get("productByHandle")
    if not node:
        raise LookupError(f"no product with handle {handle!r} on {store}")
    return normalise(node, store=store)


def load_json(path: str) -> Product:
    """Read a product from a JSON file in any of the shapes we accept."""
    with open(path, encoding="utf-8") as handle:
        return normalise(json.load(handle))


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower())
    return slug.strip("-")


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _unwrap(data: dict[str, Any]) -> dict[str, Any]:
    """Peel the wrappers the Admin API and the MCP tools put around a product."""
    for _ in range(6):
        if "node" in data and isinstance(data["node"], dict):
            data = data["node"]
            continue
        for key in ("product", "productByHandle", "data"):
            inner = data.get(key)
            if isinstance(inner, dict):
                data = inner
                break
        else:
            # search_products shape: {"products": {"edges": [{"node": {...}}]}}
            products = data.get("products")
            if isinstance(products, dict) and products.get("edges"):
                data = products["edges"][0]
                continue
            if isinstance(products, list) and products:
                data = products[0]
                continue
            break
    return data


def _collect_images(data: dict[str, Any]) -> list[Image]:
    images: list[Image] = []
    seen: set[str] = set()

    def add(img: Any) -> None:
        if not isinstance(img, dict):
            return
        url = img.get("url") or img.get("src") or img.get("originalSrc")
        if not url or url in seen:
            return
        seen.add(url)
        images.append(
            Image(
                url=url,
                alt=img.get("altText") or img.get("alt") or "",
                width=int(img.get("width") or 0),
                height=int(img.get("height") or 0),
            )
        )

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "image" in node and isinstance(node["image"], dict):
                add(node["image"])
            if {"url", "altText"} & node.keys() and "url" in node:
                add(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    # featuredMedia first so the hero shot stays at index 0
    walk(data.get("featuredMedia"))
    walk(data.get("featuredImage"))
    for key in ("media", "images"):
        walk(data.get(key))
    return images


def normalise(raw: dict[str, Any], store: str = "") -> Product:
    """Turn any accepted product shape into a `Product`."""
    data = _unwrap(raw)

    description = data.get("description") or _strip_html(data.get("descriptionHtml", ""))

    price, currency = "", ""
    price_range = data.get("priceRangeV2") or data.get("priceRange") or {}
    minimum = price_range.get("minVariantPrice") or {}
    if minimum:
        price = str(minimum.get("amount", ""))
        currency = minimum.get("currencyCode", "")
    if not price:
        variants = data.get("variants")
        if isinstance(variants, dict):
            edges = variants.get("edges") or []
            if edges:
                price = str(_unwrap(edges[0]).get("price", ""))

    # The MCP tools omit the handle; derive one so run directories stay readable.
    handle = data.get("handle") or _slugify(data.get("title", ""))

    url = data.get("onlineStoreUrl") or ""
    if not url and store and handle:
        url = f"https://{store}/products/{handle}"

    return Product(
        handle=handle,
        title=data.get("title", ""),
        description=description,
        price=price,
        currency=currency,
        url=url,
        vendor=data.get("vendor", ""),
        product_type=data.get("productType") or data.get("product_type", ""),
        tags=list(data.get("tags") or []),
        images=_collect_images(data),
    )
