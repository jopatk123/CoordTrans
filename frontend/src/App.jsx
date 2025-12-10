import React, { useState, useCallback } from 'react';
import { Layout, Tabs, Card, Form, Input, Button, Upload, message, Spin } from 'antd';
import { UploadOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Header, Content, Footer } = Layout;

// 配置 axios 默认超时
const api = axios.create({
  timeout: 30000, // 30秒超时
});

// 支持的文件类型
const ALLOWED_FILE_TYPES = [
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
  '.csv',
  '.xls',
  '.xlsx'
];

// 最大文件大小 (10MB)
const MAX_FILE_SIZE = 10 * 1024 * 1024;

// 错误消息映射
const getErrorMessage = (error) => {
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return '请求超时，请稍后重试';
  }
  if (!error.response) {
    return '网络连接失败，请检查网络';
  }
  const status = error.response?.status;
  const detail = error.response?.data?.detail;
  if (status === 400) return detail || '输入参数有误，请检查';
  if (status === 422) return '输入格式错误，请检查';
  if (status === 502) return '地图服务暂时不可用，请稍后重试';
  if (status >= 500) return '服务器错误，请稍后重试';
  return detail || '请求失败，请稍后重试';
};

const App = () => {
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [singleResult, setSingleResult] = useState(null);
  const [activeTab, setActiveTab] = useState('1');

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  // Single Geocode
  const onFinishGeo = useCallback(async (values) => {
    // 防止重复提交
    if (loading) return;
    
    // 前端输入验证
    const address = values.address?.trim();
    if (!address) {
      message.warning('请输入有效的地址');
      return;
    }
    
    setLoading(true);
    setSingleResult(null);
    try {
      const res = await api.post('/api/geo', {
        address: address,
        city: values.city?.trim() || null
      });
      if (res.data?.status === 'success' && res.data?.data) {
        setSingleResult(res.data.data);
        message.success('查询成功');
      } else {
        message.warning(res.data?.msg || '未找到相关地址信息');
      }
    } catch (error) {
      console.error('Geocode error:', error);
      message.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [loading]);

  // Single Regeocode
  const onFinishRegeo = useCallback(async (values) => {
    // 防止重复提交
    if (loading) return;
    
    // 前端经纬度格式验证
    const location = values.location?.trim();
    if (!location) {
      message.warning('请输入经纬度');
      return;
    }
    
    // 验证经纬度格式
    const parts = location.split(',').map(s => s.trim());
    if (parts.length !== 2) {
      message.warning('经纬度格式错误，请使用"经度,纬度"格式');
      return;
    }
    
    const [lon, lat] = parts.map(Number);
    if (isNaN(lon) || isNaN(lat)) {
      message.warning('经纬度必须是数字');
      return;
    }
    
    // 验证经纬度范围
    if (lon < -180 || lon > 180 || lat < -90 || lat > 90) {
      message.warning('经纬度超出有效范围（经度: -180~180，纬度: -90~90）');
      return;
    }
    
    setLoading(true);
    setSingleResult(null);
    try {
      const res = await api.post('/api/regeo', { location: `${lon},${lat}` });
      if (res.data?.status === 'success' && res.data?.data) {
        setSingleResult(res.data.data);
        message.success('查询成功');
      } else {
        message.warning(res.data?.msg || '未找到相关位置信息');
      }
    } catch (error) {
      console.error('Regeocode error:', error);
      message.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [loading]);

  // 文件上传前验证
  const beforeUpload = useCallback((file) => {
    // 检查文件类型
    const isValidType = ALLOWED_FILE_TYPES.some(type => {
      if (type.startsWith('.')) {
        return file.name.toLowerCase().endsWith(type);
      }
      return file.type === type;
    });
    
    if (!isValidType) {
      message.error('只支持 Excel (.xlsx, .xls) 或 CSV 文件');
      return Upload.LIST_IGNORE;
    }
    
    // 检查文件大小
    if (file.size > MAX_FILE_SIZE) {
      message.error('文件大小不能超过 10MB');
      return Upload.LIST_IGNORE;
    }
    
    // 检查文件名
    if (!file.name || file.name.length > 200) {
      message.error('文件名无效或过长');
      return Upload.LIST_IGNORE;
    }
    
    return true;
  }, []);

  // Batch Upload
  const uploadProps = (type) => ({
    name: 'file',
    accept: '.csv,.xls,.xlsx',
    maxCount: 1,
    showUploadList: true,
    beforeUpload: beforeUpload,
    customRequest: async ({ file, onSuccess, onError, onProgress }) => {
      // 防止并发上传
      if (uploadLoading) {
        message.warning('请等待当前文件处理完成');
        onError(new Error('Upload in progress'));
        return;
      }
      
      setUploadLoading(true);
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const res = await api.post(`/api/batch/file/${type}`, formData, {
          responseType: 'blob',
          timeout: 120000, // 批量处理超时 2分钟
          onUploadProgress: (progressEvent) => {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress({ percent });
          }
        });
        
        // 检查响应是否是错误
        if (res.data.type === 'application/json') {
          const text = await res.data.text();
          const errorData = JSON.parse(text);
          throw new Error(errorData.detail || '处理失败');
        }
        
        // 生成安全的文件名
        const safeName = file.name.replace(/[^a-zA-Z0-9._\-\u4e00-\u9fa5]/g, '_');
        downloadBlob(new Blob([res.data]), `processed_${safeName}.xlsx`);
        message.success(`${file.name} 处理成功`);
        onSuccess({}, file);
      } catch (err) {
        console.error('Batch upload error:', err);
        const errorMsg = err.message || getErrorMessage(err);
        message.error(`${file.name} 处理失败: ${errorMsg}`);
        onError(err);
      } finally {
        setUploadLoading(false);
      }
    }
  });

  const GeoTab = () => (
    <div className="space-y-6">
      <Card title="单条查询" variant="borderless">
        <Form layout="inline" onFinish={onFinishGeo}>
          <Form.Item 
            name="address" 
            rules={[
              { required: true, message: '请输入地址' },
              { min: 2, message: '地址至少2个字符' },
              { max: 200, message: '地址不能超过200个字符' },
              { whitespace: true, message: '地址不能为空白' }
            ]}
          >
            <Input 
              placeholder="请输入详细地址" 
              style={{ width: 300 }} 
              maxLength={200}
              allowClear
              disabled={loading}
            />
          </Form.Item>
          <Form.Item 
            name="city"
            rules={[
              { max: 50, message: '城市名不能超过50个字符' }
            ]}
          >
            <Input 
              placeholder="城市 (可选)" 
              maxLength={50}
              allowClear
              disabled={loading}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading} disabled={loading}>
              查询
            </Button>
          </Form.Item>
        </Form>
        {singleResult && singleResult.location && (
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <p><strong>经纬度:</strong> {singleResult.location || '-'}</p>
            <p><strong>格式化地址:</strong> {singleResult.formatted_address || '-'}</p>
            <p><strong>行政区:</strong> {singleResult.province || ''} {singleResult.city || ''} {singleResult.district || ''}</p>
          </div>
        )}
      </Card>

      <Card title="批量处理 (Excel/CSV)" variant="borderless">
        <p className="mb-4 text-gray-500">请上传包含"地址"列的 Excel 或 CSV 文件（最多1000行，文件不超过10MB）。</p>
        <Spin spinning={uploadLoading} tip="处理中...">
          <Upload {...uploadProps('geo')}>
            <Button icon={<UploadOutlined />} disabled={uploadLoading} loading={uploadLoading}>
              上传文件并处理
            </Button>
          </Upload>
        </Spin>
      </Card>
    </div>
  );

  const RegeoTab = () => (
    <div className="space-y-6">
      <Card title="单条查询" variant="borderless">
        <Form layout="inline" onFinish={onFinishRegeo}>
          <Form.Item 
            name="location" 
            rules={[
              { required: true, message: '请输入经纬度' },
              { 
                pattern: /^-?\d+\.?\d*\s*,\s*-?\d+\.?\d*$/, 
                message: '格式错误，请使用 "经度,纬度" 格式' 
              }
            ]}
          >
            <Input 
              placeholder="经度,纬度 (如: 116.48,39.99)" 
              style={{ width: 300 }} 
              maxLength={50}
              allowClear
              disabled={loading}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading} disabled={loading}>
              查询
            </Button>
          </Form.Item>
        </Form>
        {singleResult && singleResult.formatted_address && (
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <p><strong>地址:</strong> {singleResult.formatted_address || '-'}</p>
            <p><strong>乡镇/街道:</strong> {singleResult.addressComponent?.township || '-'}</p>
          </div>
        )}
      </Card>

      <Card title="批量处理 (Excel/CSV)" variant="borderless">
        <p className="mb-4 text-gray-500">请上传包含"经度"和"纬度"列的 Excel 或 CSV 文件（最多1000行，文件不超过10MB）。</p>
        <Spin spinning={uploadLoading} tip="处理中...">
          <Upload {...uploadProps('regeo')}>
            <Button icon={<UploadOutlined />} disabled={uploadLoading} loading={uploadLoading}>
              上传文件并处理
            </Button>
          </Upload>
        </Spin>
      </Card>
    </div>
  );

  const items = [
    { key: '1', label: '地址转经纬度', children: <GeoTab /> },
    { key: '2', label: '经纬度转地址', children: <RegeoTab /> },
  ];

  return (
    <Layout className="min-h-screen">
      <Header className="flex items-center">
        <div className="text-white text-xl font-bold">CoordTrans 经纬度转换工具</div>
      </Header>
      <Content className="p-8 max-w-5xl mx-auto w-full">
        <Tabs
          activeKey={activeTab}
          items={items}
          onChange={(key) => {
            setActiveTab(key);
            setSingleResult(null);
          }}
        />
      </Content>
      <Footer className="text-center">
        CoordTrans ©2024 Created by AI Assistant
      </Footer>
    </Layout>
  );
};

export default App;
