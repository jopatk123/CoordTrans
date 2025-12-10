import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import { message } from 'antd'
import axios from 'axios'
import App from '../App.jsx'

vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
  },
}))

describe('App integration', () => {
  beforeEach(() => {
    axios.post.mockReset()
    vi.spyOn(message, 'success').mockImplementation(() => {})
    vi.spyOn(message, 'error').mockImplementation(() => {})
  })

  it('submits geocode requests and renders results', async () => {
    axios.post.mockResolvedValueOnce({
      data: {
        status: 'success',
        data: {
          location: '116.48,39.99',
          formatted_address: '测试地址',
          province: '北京市',
          city: '北京市',
          district: '朝阳区',
        },
      },
    })

    render(<App />)

    const addressInput = screen.getByPlaceholderText('请输入详细地址')
    fireEvent.change(addressInput, { target: { value: '北京市朝阳区阜通东大街6号' } })

    const submitButton = screen.getByRole('button', { name: /查询/ })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/geo', expect.objectContaining({
        address: '北京市朝阳区阜通东大街6号',
      }))
    })

    expect(await screen.findByText(/经纬度:/)).toBeInTheDocument()
    expect(await screen.findByText(/格式化地址:/)).toBeInTheDocument()
  })

  it('submits regeocode requests on the second tab', async () => {
    axios.post.mockResolvedValueOnce({
      data: {
        status: 'success',
        data: {
          formatted_address: '上海市浦东新区',
          addressComponent: {
            township: '花木街道',
          },
        },
      },
    })

    render(<App />)

    const regeoTab = screen.getByRole('tab', { name: '经纬度转地址' })
    fireEvent.click(regeoTab)

    const locationInput = screen.getByPlaceholderText('经度,纬度 (如: 116.48,39.99)')
    fireEvent.change(locationInput, { target: { value: '121.5,31.22' } })

    const submitButton = screen.getByRole('button', { name: /查询/ })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/regeo', expect.objectContaining({
        location: '121.5,31.22',
      }))
    })

    expect(await screen.findByText(/地址:/)).toBeInTheDocument()
  })
})
