import React, { useState } from 'react'
import { Card, Row, Col, Progress, Button, Result, Select, Spin, Alert, Statistic, Tag, Divider, Badge } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, QuestionCircleOutlined, BarChartOutlined, LineChartOutlined, ReloadOutlined } from '@ant-design/icons'
import { getScore, getDecision } from '../services/api'

const { Option } = Select

interface ScoreResult {
  total_score: number
  technical_score: number
  fundamental_score: number
  sentiment_score: number
  risk_score: number
  liquidity_score: number
}

interface DecisionResult {
  action: 'buy' | 'sell' | 'hold'
  confidence: number
  entry_conditions: string[]
  exit_conditions: string[]
  stop_loss?: number
  take_profit?: number
  reasoning: string
}

const ScoringDecision: React.FC = () => {
  const [symbol, setSymbol] = useState<string>('000001')
  const [loading, setLoading] = useState(false)
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null)
  const [decisionResult, setDecisionResult] = useState<DecisionResult | null>(null)
  const [error, setError] = useState('')

  const handleGetScore = async () => {
    setLoading(true)
    setError('')
    setScoreResult(null)

    try {
      const response = await getScore(symbol)
      if (response.data.success) {
        setScoreResult(response.data.data)
      } else {
        setError(response.data.message || '获取评分失败')
      }
    } catch (err: any) {
      setError('网络错误，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  const handleGetDecision = async () => {
    setLoading(true)
    setError('')
    setDecisionResult(null)

    try {
      const response = await getDecision(symbol)
      if (response.data.success) {
        setDecisionResult(response.data.data)
      } else {
        setError(response.data.message || '获取决策失败')
      }
    } catch (err: any) {
      setError('网络错误，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async () => {
    setLoading(true)
    setError('')
    setScoreResult(null)
    setDecisionResult(null)

    try {
      const [scoreRes, decisionRes] = await Promise.all([
        getScore(symbol),
        getDecision(symbol),
      ])

      if (scoreRes.data.success) {
        setScoreResult(scoreRes.data.data)
      } else {
        setError(scoreRes.data.message || '获取评分失败')
      }

      if (decisionRes.data.success) {
        setDecisionResult(decisionRes.data.data)
      } else {
        if (!scoreRes.data.success) {
          setError(decisionRes.data.message || '获取决策失败')
        }
      }
    } catch (err: any) {
      setError('网络错误，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'buy':
        return <CheckCircleOutlined />
      case 'sell':
        return <CloseCircleOutlined />
      default:
        return <QuestionCircleOutlined />
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'buy':
        return 'success'
      case 'sell':
        return 'error'
      default:
        return 'warning'
    }
  }

  const getActionText = (action: string) => {
    switch (action) {
      case 'buy':
        return '买入'
      case 'sell':
        return '卖出'
      default:
        return '持有'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#52c41a'
    if (score >= 60) return '#1890ff'
    if (score >= 40) return '#faad14'
    return '#ff4d4f'
  }

  const getScoreStatus = (score: number) => {
    if (score >= 80) return 'success'
    if (score >= 60) return 'normal'
    if (score >= 40) return 'exception'
    return 'exception'
  }

  return (
    <div>
      <h2>评分决策</h2>

      {error && (
        <Alert
          message="错误"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setError('')}
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={12} md={8}>
            <div style={{ marginBottom: 8 }}>选择股票</div>
            <Select
              value={symbol}
              onChange={setSymbol}
              style={{ width: '100%' }}
              placeholder="选择股票"
            >
              <Option value="000001">000001 平安银行</Option>
              <Option value="000002">000002 万科A</Option>
              <Option value="000858">000858 五粮液</Option>
              <Option value="600519">600519 贵州茅台</Option>
              <Option value="300750">300750 宁德时代</Option>
            </Select>
          </Col>
          <Col xs={24} sm={6} md={8}>
            <div style={{ marginBottom: 8 }}>&nbsp;</div>
            <Button
              type="primary"
              icon={<BarChartOutlined />}
              onClick={handleAnalyze}
              loading={loading}
              disabled={loading}
              style={{ marginRight: 8 }}
            >
              综合分析
            </Button>
          </Col>
        </Row>
        <Row gutter={16} style={{ marginTop: 8 }}>
          <Col xs={24}>
            <Button
              icon={<LineChartOutlined />}
              onClick={handleGetScore}
              loading={loading}
              disabled={loading}
              style={{ marginRight: 8 }}
            >
              仅获取评分
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleGetDecision}
              loading={loading}
              disabled={loading}
            >
              仅获取决策
            </Button>
          </Col>
        </Row>
      </Card>

      {loading && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="正在分析中..." />
        </Card>
      )}

      <Row gutter={16}>
        {scoreResult && !loading && (
          <Col xs={24} lg={12} style={{ marginBottom: 16 }}>
            <Card title="股票评分">
              <div style={{ textAlign: 'center', marginBottom: 24 }}>
                <Progress
                  type="circle"
                  percent={scoreResult.total_score}
                  strokeColor={getScoreColor(scoreResult.total_score)}
                  format={(percent) => (
                    <div>
                      <div style={{ fontSize: 32, fontWeight: 'bold' }}>{percent}</div>
                      <div style={{ fontSize: 14, color: '#666' }}>综合评分</div>
                    </div>
                  )}
                  width={140}
                />
              </div>

              <Divider />

              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>技术面评分</span>
                  <span style={{ color: getScoreColor(scoreResult.technical_score), fontWeight: 'bold' }}>
                    {scoreResult.technical_score}分
                  </span>
                </div>
                <Progress
                  percent={scoreResult.technical_score}
                  strokeColor={getScoreColor(scoreResult.technical_score)}
                  status={getScoreStatus(scoreResult.technical_score)}
                  showInfo={false}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>基本面评分</span>
                  <span style={{ color: getScoreColor(scoreResult.fundamental_score), fontWeight: 'bold' }}>
                    {scoreResult.fundamental_score}分
                  </span>
                </div>
                <Progress
                  percent={scoreResult.fundamental_score}
                  strokeColor={getScoreColor(scoreResult.fundamental_score)}
                  status={getScoreStatus(scoreResult.fundamental_score)}
                  showInfo={false}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>情绪面评分</span>
                  <span style={{ color: getScoreColor(scoreResult.sentiment_score), fontWeight: 'bold' }}>
                    {scoreResult.sentiment_score}分
                  </span>
                </div>
                <Progress
                  percent={scoreResult.sentiment_score}
                  strokeColor={getScoreColor(scoreResult.sentiment_score)}
                  status={getScoreStatus(scoreResult.sentiment_score)}
                  showInfo={false}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>风险评分</span>
                  <span style={{ color: getScoreColor(scoreResult.risk_score), fontWeight: 'bold' }}>
                    {scoreResult.risk_score}分
                  </span>
                </div>
                <Progress
                  percent={scoreResult.risk_score}
                  strokeColor={getScoreColor(scoreResult.risk_score)}
                  status={getScoreStatus(scoreResult.risk_score)}
                  showInfo={false}
                />
              </div>

              <div style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>流动性评分</span>
                  <span style={{ color: getScoreColor(scoreResult.liquidity_score), fontWeight: 'bold' }}>
                    {scoreResult.liquidity_score}分
                  </span>
                </div>
                <Progress
                  percent={scoreResult.liquidity_score}
                  strokeColor={getScoreColor(scoreResult.liquidity_score)}
                  status={getScoreStatus(scoreResult.liquidity_score)}
                  showInfo={false}
                />
              </div>
            </Card>
          </Col>
        )}

        {decisionResult && !loading && (
          <Col xs={24} lg={scoreResult ? 12 : 24} style={{ marginBottom: 16 }}>
            <Card title="交易决策">
              <Result
                icon={getActionIcon(decisionResult.action)}
                status={getActionColor(decisionResult.action) as any}
                title={
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                    <span>建议操作：{getActionText(decisionResult.action)}</span>
                    <Tag color={decisionResult.confidence >= 70 ? 'green' : decisionResult.confidence >= 50 ? 'blue' : 'orange'}>
                      置信度 {decisionResult.confidence}%
                    </Tag>
                  </div>
                }
                subTitle={decisionResult.reasoning}
              />

              <Divider />

              <Row gutter={16} style={{ marginBottom: 16 }}>
                {decisionResult.stop_loss && (
                  <Col span={12}>
                    <Card size="small" style={{ backgroundColor: '#fff1f0' }}>
                      <Statistic
                        title="止损价位"
                        value={decisionResult.stop_loss}
                        precision={2}
                        prefix="¥"
                        valueStyle={{ color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                )}
                {decisionResult.take_profit && (
                  <Col span={12}>
                    <Card size="small" style={{ backgroundColor: '#f6ffed' }}>
                      <Statistic
                        title="止盈价位"
                        value={decisionResult.take_profit}
                        precision={2}
                        prefix="¥"
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                )}
              </Row>

              {decisionResult.entry_conditions.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 8, fontWeight: 'bold' }}>
                    <Badge color="green" /> 入场条件
                  </div>
                  <ul style={{ paddingLeft: 20, margin: 0 }}>
                    {decisionResult.entry_conditions.map((condition, index) => (
                      <li key={index} style={{ marginBottom: 4, color: '#52c41a' }}>
                        {condition}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {decisionResult.exit_conditions.length > 0 && (
                <div>
                  <div style={{ marginBottom: 8, fontWeight: 'bold' }}>
                    <Badge color="red" /> 失效条件
                  </div>
                  <ul style={{ paddingLeft: 20, margin: 0 }}>
                    {decisionResult.exit_conditions.map((condition, index) => (
                      <li key={index} style={{ marginBottom: 4, color: '#ff4d4f' }}>
                        {condition}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          </Col>
        )}
      </Row>

      {!scoreResult && !decisionResult && !loading && (
        <Card style={{ textAlign: 'center', padding: 60 }}>
          <BarChartOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
          <p style={{ marginTop: 16, color: '#999' }}>请选择股票并点击分析按钮获取评分和决策建议</p>
        </Card>
      )}
    </div>
  )
}

export default ScoringDecision
