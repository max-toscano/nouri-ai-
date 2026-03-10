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
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

export async function searchFoods(query: string): Promise<FoodSearchResult[]> {
  const url = `https://world.openfoodfacts.org/cgi/search.pl?search_terms=${encodeURIComponent(query)}&search_simple=1&action=process&json=1&page_size=20`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Search request failed: ${response.status}`);
  }

  const data = await response.json();

  if (!Array.isArray(data.products)) {
    return [];
  }

  return data.products.map((product: any): FoodSearchResult => ({
    id: product.code ?? "",
    name: product.product_name ?? "Unknown",
    brand: product.brands ?? "Unknown",
    imageUrl: product.image_front_small_url ?? "",
  }));
}

export async function getFoodDetails(barcode: string): Promise<FoodDetails> {
  const url = `https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(barcode)}.json`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Food details request failed: ${response.status}`);
  }

  const data = await response.json();

  if (data.status !== 1 || !data.product) {
    throw new Error(`Product not found for barcode: ${barcode}`);
  }

  const { product } = data;
  const nutriments = product.nutriments ?? {};

  return {
    id: barcode,
    name: product.product_name ?? "Unknown",
    brand: product.brands ?? "Unknown",
    calories: nutriments["energy-kcal"] ?? 0,
    protein: nutriments["proteins"] ?? 0,
    carbs: nutriments["carbohydrates"] ?? 0,
    fat: nutriments["fat"] ?? 0,
  };
}
