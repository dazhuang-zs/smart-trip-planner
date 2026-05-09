import React from 'react'

export default function TripResult({ result, isLoading, error }) {
  if (error) {
    return (
      <div className="trip-result error">
        <div className="error-state">
          <span className="error-icon">⚠️</span>
          <h3>出错了</h3>
          <p>{error}</p>
        </div>
      </div>
    )
  }
  if (!result && !isLoading) {
    return (
      <div className="trip-result empty">
        <div className="empty-state">
          <span className="empty-icon">🧭</span>
          <h3>等待你的行程需求</h3>
          <p>在左侧输入你想要去的目的地和偏好，AI 将为你生成个性化行程</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="trip-result loading">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>AI 正在为你规划行程...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="trip-result">
      <h2>行程规划结果</h2>
      <div className="result-content">
        {result.trip_title && <h3>{result.trip_title}</h3>}
        {result.days && (
          <div className="meta">
            <span className="days">📅 {result.days} 天</span>
            {result.total_cost && <span className="cost">💰 {result.total_cost}</span>}
          </div>
        )}
        {result.highlights && (
          <div className="highlights">
            <h4>行程亮点</h4>
            <ul>
              {result.highlights.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        {result.itinerary && (
          <div className="itinerary">
            <h4>详细行程</h4>
            {result.itinerary.map((day, i) => (
              <div key={i} className="day">
                <h5>Day {i + 1}: {day.title}</h5>
                <ul>
                  {day.items?.map((item, j) => (
                    <li key={j}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
        {result.tips && (
          <div className="tips">
            <h4>💡 小贴士</h4>
            <ul>
              {result.tips.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}