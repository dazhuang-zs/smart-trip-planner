import React, { useState } from 'react'

export default function TripInput({ onSubmit, isLoading }) {
  const [input, setInput] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    onSubmit(input)
  }

  return (
    <div className="trip-input">
      <h2>规划我的行程</h2>
      <form onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="例如：我想去上海旅游3天，喜欢自然风景和美食，不想太累，有什么推荐？"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? (
            <span className="loading">生成中...</span>
          ) : (
            <>✨ 开始规划</>
          )}
        </button>
      </form>
      <div className="tips">
        <p>💡 提示：描述你的目的地、天数、偏好和预算，获得个性化行程</p>
      </div>
    </div>
  )
}