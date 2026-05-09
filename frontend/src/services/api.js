import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function generateTrip(userInput) {
  const res = await axios.post(`${API_BASE}/api/v1/trip/generate`, {
    user_input: userInput
  }, {
    timeout: 60000
  })
  return res.data
}