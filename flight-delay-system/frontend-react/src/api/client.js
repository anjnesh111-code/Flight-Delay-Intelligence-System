import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL;

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 15000,
})

export function extractEnvelope(payload) {
  if (payload && typeof payload === 'object' && payload.data && typeof payload.data === 'object') {
    return payload.data
  }
  return payload
}

export async function predictFlight(flightNumber) {
  const response = await apiClient.post('/predict', { flight_number: flightNumber })
  return extractEnvelope(response.data)
}

export async function getAirlinePerformance() {
  const response = await apiClient.get('/airlines/performance')
  return extractEnvelope(response.data)
}

