import Papa from 'papaparse'

export async function loadJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(path)
    if (!response.ok) {
      return null
    }
    return await response.json()
  } catch {
    return null
  }
}

export async function loadCsv<T>(path: string): Promise<T[] | null> {
  try {
    const response = await fetch(path)
    if (!response.ok) {
      return null
    }
    const text = await response.text()
    const result = Papa.parse<T>(text, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: true
    })
    return result.data
  } catch {
    return null
  }
}

export async function listDirectory(path: string): Promise<string[] | null> {
  try {
    const response = await fetch(path)
    if (!response.ok) {
      return null
    }
    return await response.json()
  } catch {
    return null
  }
}