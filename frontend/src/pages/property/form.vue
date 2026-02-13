<template>
  <view class="form-page">
    <view class="section-title">基础信息</view>
    <view class="form-group">
      <text class="label">房源名称 *</text>
      <input v-model="form.name" placeholder="例: 西湖畔民宿" class="input" />
    </view>
    <view class="form-group">
      <text class="label">地址 *</text>
      <input v-model="form.address" placeholder="例: 杭州市西湖区北山路88号" class="input" />
    </view>
    <view class="form-group">
      <text class="label">房型 *</text>
      <picker :range="roomTypes" @change="onRoomTypeChange">
        <view class="picker-value">{{ form.room_type || '请选择' }}</view>
      </picker>
    </view>
    <view class="form-group">
      <text class="label">面积(㎡) *</text>
      <input v-model="form.area" type="digit" placeholder="例: 80" class="input" />
    </view>
    <view class="form-group">
      <text class="label">描述</text>
      <textarea v-model="form.description" placeholder="房源描述（可选）" class="textarea" />
    </view>

    <view class="section-title">定价偏好</view>
    <view class="form-group">
      <text class="label">最低可接受价(元)</text>
      <input v-model="form.min_price" type="digit" placeholder="例: 300" class="input" />
    </view>
    <view class="form-group">
      <text class="label">最高价格(元)</text>
      <input v-model="form.max_price" type="digit" placeholder="例: 800" class="input" />
    </view>
    <view class="form-group">
      <text class="label">期望收益率</text>
      <input v-model="form.expected_return_rate" type="digit" placeholder="例: 0.15 (即15%)" class="input" />
    </view>
    <view class="form-group">
      <text class="label">空置容忍度</text>
      <input v-model="form.vacancy_tolerance" type="digit" placeholder="例: 0.2 (即20%)" class="input" />
    </view>

    <button class="submit-btn" @click="handleSubmit" :disabled="submitting">
      {{ isEdit ? '更新' : '创建' }}
    </button>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { usePropertyStore } from '../../stores/property'

const propertyStore = usePropertyStore()
const roomTypes = ['整套', '单间', '合住', '别墅', '公寓']
const isEdit = ref(false)
const editId = ref<number | null>(null)
const submitting = ref(false)

const form = reactive({
  name: '',
  address: '',
  room_type: '',
  area: '',
  description: '',
  min_price: '',
  max_price: '',
  expected_return_rate: '',
  vacancy_tolerance: '',
})

onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const id = currentPage.$page?.options?.id || currentPage.options?.id
  if (id) {
    isEdit.value = true
    editId.value = Number(id)
    loadProperty(Number(id))
  }
})

async function loadProperty(id: number) {
  await propertyStore.fetchOne(id)
  const prop = propertyStore.currentProperty
  if (prop) {
    form.name = prop.name
    form.address = prop.address
    form.room_type = prop.room_type
    form.area = String(prop.area)
    form.description = prop.description || ''
    form.min_price = prop.min_price ? String(prop.min_price) : ''
    form.max_price = prop.max_price ? String(prop.max_price) : ''
    form.expected_return_rate = prop.expected_return_rate ? String(prop.expected_return_rate) : ''
    form.vacancy_tolerance = prop.vacancy_tolerance ? String(prop.vacancy_tolerance) : ''
  }
}

function onRoomTypeChange(e: any) {
  form.room_type = roomTypes[e.detail.value]
}

async function handleSubmit() {
  if (!form.name || !form.address || !form.room_type || !form.area) {
    uni.showToast({ title: '请填写必填项', icon: 'none' })
    return
  }

  const data = {
    name: form.name,
    address: form.address,
    room_type: form.room_type,
    area: Number(form.area),
    description: form.description || null,
    min_price: form.min_price ? Number(form.min_price) : null,
    max_price: form.max_price ? Number(form.max_price) : null,
    expected_return_rate: form.expected_return_rate ? Number(form.expected_return_rate) : null,
    vacancy_tolerance: form.vacancy_tolerance ? Number(form.vacancy_tolerance) : null,
  }

  submitting.value = true
  try {
    if (isEdit.value && editId.value) {
      await propertyStore.update(editId.value, data)
      uni.showToast({ title: '更新成功', icon: 'success' })
    } else {
      await propertyStore.create(data)
      uni.showToast({ title: '创建成功', icon: 'success' })
    }
    setTimeout(() => uni.navigateBack(), 500)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-page {
  padding: 32rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.section-title {
  font-size: 30rpx;
  font-weight: bold;
  margin: 24rpx 0 16rpx;
}
.form-group {
  background: #fff;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  margin-bottom: 12rpx;
}
.label {
  font-size: 24rpx;
  color: #666;
  margin-bottom: 8rpx;
  display: block;
}
.input {
  font-size: 28rpx;
  padding: 8rpx 0;
}
.textarea {
  font-size: 28rpx;
  width: 100%;
  min-height: 120rpx;
}
.picker-value {
  font-size: 28rpx;
  padding: 8rpx 0;
  color: #333;
}
.submit-btn {
  margin-top: 40rpx;
  background: #1890ff;
  color: #fff;
  border-radius: 12rpx;
  font-size: 32rpx;
}
</style>
