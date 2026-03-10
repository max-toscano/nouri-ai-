// Open Food Facts API — no credentials required
// Note: nutrition values are per 100g unless a serving size is specified.

export interface FoodSearchResult {
  id: string;
  name: string;
  brand: string;
  imageUrl: string;
}

export interface FoodDetails {
  id: string;
  name: string;
  brand: string;
  imageUrl: string;
  /** kcal per 100g */
  caloriesKcal: number;
  /** grams protein per 100g */
  proteinG: number;
  /** grams carbohydrates per 100g */
  carbsG: number;
  /** grams fat per 100g */
  fatG: number;
  servingSize: string | null;
}

export async function searchFoods(query: string): Promise<FoodSearchResult[]> {
  const url =
    `https://world.openfoodfacts.org/cgi/search.pl` +
    `?search_terms=${encodeURIComponent(query)}` +
    `&search_simple=1&action=process&json=1&page_size=20`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Open Food Facts search failed: ${response.status}`);
  }

  const data = await response.json();

  if (!Array.isArray(data.products)) {
    return [];
  }

  return data.products.map((product: any): FoodSearchResult => ({
    id: product.code ?? "",
    name: product.product_name || product.generic_name || "Unknown",
    brand: product.brands ?? "",
    imageUrl: product.image_front_small_url || product.image_url || "",
  }));
}

export async function getFoodDetails(barcode: string): Promise<FoodDetails> {
  const url = `https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(barcode)}.json`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Open Food Facts product fetch failed: ${response.status}`);
  }

  const data = await response.json();

  if (data.status !== 1 || !data.product) {
    throw new Error(`Product not found for barcode: ${barcode}`);
  }

  const { product } = data;
  const n = product.nutriments ?? {};

  return {
    id: product.code ?? barcode,
    name: product.product_name || product.generic_name || "Unknown",
    brand: product.brands ?? "",
    imageUrl: product.image_front_url || product.image_url || "",
    caloriesKcal: n["energy-kcal_100g"] ?? n["energy-kcal"] ?? 0,
    proteinG: n["proteins_100g"] ?? n["proteins"] ?? 0,
    carbsG: n["carbohydrates_100g"] ?? n["carbohydrates"] ?? 0,
    fatG: n["fat_100g"] ?? n["fat"] ?? 0,
    servingSize: product.serving_size ?? null,
  };
}
