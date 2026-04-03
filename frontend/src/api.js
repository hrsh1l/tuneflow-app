export async function fetchData(endpoint) {
  const response = await fetch(`http://localhost:5000/${endpoint}`);
  const data = await response.json();
  return data;
}