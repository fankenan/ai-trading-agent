import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 系统状态
export const getStatus = () => api.get('/status')

// 数据源管理
export const getDataSource = () => api.get('/datasource')
export const switchDataSource = (source: string) =>
  api.post('/datasource', { source })

// 市场数据
export const getMarketData = (symbol: string, days: number = 365) =>
  api.get('/market', { params: { symbol, days } })

// 回测
export const runBacktest = (symbol: string, strategy: string, days: number) =>
  api.post('/backtest', { symbol, strategy, days })

// 评分
export const getScore = (symbol: string) =>
  api.get('/score', { params: { symbol } })

// 决策
export const getDecision = (symbol: string) =>
  api.get('/decision', { params: { symbol } })

// 新闻
export const getNews = () => api.get('/news')
export const submitNews = (title: string, content: string, source: string) =>
  api.post('/news', { title, content, source })

// 北向资金
export const getNorthFlow = () => api.get('/north_flow')

// 报告
export const getReport = (params: any) => api.get('/report', { params })

export default api
