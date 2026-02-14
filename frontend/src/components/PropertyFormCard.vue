<template>
  <view class="property-form-card" :class="{ submitted: form.submitted }">
    <view class="form-card-header">
      <text class="form-card-icon">📋</text>
      <text class="form-card-title">房源信息录入</text>
    </view>

    <view class="form-card-body">
      <view v-for="field in form.fields" :key="field.key" class="form-field">
        <text class="field-label">
          {{ field.label }}
          <text v-if="field.required" class="required-mark">*</text>
        </text>

        <!-- text input -->
        <input
          v-if="field.type === 'text'"
          v-model="formData[field.key]"
          :placeholder="focusedField === field.key ? '' : (field.placeholder || '')"
          :disabled="form.submitted"
          class="field-input"
          :class="{ 'field-focused': focusedField === field.key }"
          placeholder-style="color: #64748B; font-size: 28rpx;"
          @focus="focusedField = field.key"
          @blur="focusedField = ''"
        />

        <!-- number input -->
        <input
          v-else-if="field.type === 'number'"
          v-model="formData[field.key]"
          type="digit"
          :placeholder="focusedField === field.key ? '' : (field.placeholder || '')"
          :disabled="form.submitted"
          class="field-input"
          :class="{ 'field-focused': focusedField === field.key }"
          placeholder-style="color: #64748B; font-size: 28rpx;"
          @focus="focusedField = field.key"
          @blur="focusedField = ''"
        />

        <!-- textarea -->
        <textarea
          v-else-if="field.type === 'textarea'"
          v-model="formData[field.key]"
          :placeholder="focusedField === field.key ? '' : (field.placeholder || '')"
          :disabled="form.submitted"
          :auto-height="true"
          class="field-textarea"
          :class="{ 'field-focused': focusedField === field.key }"
          placeholder-style="color: #64748B; font-size: 28rpx;"
          @focus="focusedField = field.key"
          @blur="focusedField = ''"
        />

        <!-- picker -->
        <picker
          v-else-if="field.type === 'picker'"
          :range="field.options || []"
          :disabled="form.submitted"
          @change="(e: any) => formData[field.key] = (field.options || [])[e.detail.value]"
        >
          <view class="field-picker">
            <text :class="formData[field.key] ? 'picker-text' : 'picker-placeholder'">
              {{ formData[field.key] || '请选择' }}
            </text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>
    </view>

    <view class="form-card-footer">
      <view v-if="form.submitted" class="submitted-badge">
        <text class="submitted-icon">✅</text>
        <text class="submitted-text">已提交</text>
      </view>
      <view v-else class="submit-btn" @click="handleSubmit">
        <text class="submit-text">提交表单</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

const props = defineProps<{
  form: {
    form_type: string
    fields: Array<{
      key: string
      label: string
      type: string
      required: boolean
      placeholder?: string
      options?: string[]
    }>
    submitted?: boolean
  }
}>()

const emit = defineEmits<{
  (e: 'submit', data: Record<string, any>): void
}>()

// Initialize reactive form data
const formData = reactive<Record<string, string>>({})
const focusedField = ref('')
for (const field of props.form.fields) {
  formData[field.key] = ''
}

function handleSubmit() {
  // Validate required fields
  for (const field of props.form.fields) {
    if (field.required && !formData[field.key]?.trim()) {
      uni.showToast({ title: `请填写${field.label}`, icon: 'none' })
      return
    }
  }

  // Build structured data with type coercion
  const data: Record<string, any> = {}
  for (const field of props.form.fields) {
    const val = formData[field.key]?.trim()
    if (!val) continue
    if (field.type === 'number') {
      data[field.key] = Number(val)
    } else {
      data[field.key] = val
    }
  }

  emit('submit', data)
}
</script>

<style scoped lang="scss">
.property-form-card {
  background: #1E293B;
  border-radius: 24rpx;
  margin: 20rpx 0;
  overflow: hidden;
  border: 1rpx solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.2);

  &.submitted {
    opacity: 0.7;
    pointer-events: none;
  }
}

/* ===== Header ===== */
.form-card-header {
  padding: 28rpx 32rpx;
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.form-card-icon {
  font-size: 36rpx;
}

.form-card-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1rpx;
}

/* ===== Body ===== */
.form-card-body {
  padding: 32rpx 32rpx 8rpx;
}

.form-field {
  margin-bottom: 32rpx;
}

.field-label {
  font-size: 28rpx;
  color: #CBD5E1;
  margin-bottom: 12rpx;
  display: block;
  font-weight: 500;
}

.required-mark {
  color: #F87171;
  margin-left: 4rpx;
  font-weight: 700;
}

/* ===== Input fields — sized for mobile touch targets ===== */
.field-input {
  width: 100%;
  height: 88rpx;
  padding: 0 28rpx;
  font-size: 30rpx;
  line-height: 88rpx;
  color: #F1F5F9;
  background: #0F172A;
  border: 1rpx solid rgba(255, 255, 255, 0.1);
  border-radius: 16rpx;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;

  &.field-focused {
    border-color: #818CF8;
    box-shadow: 0 0 0 4rpx rgba(129, 140, 248, 0.2);
    background: #0F172A;
  }

  &:disabled {
    opacity: 0.5;
  }
}

/* Override uni-app default uni-input inner */
:deep(.uni-input-input) {
  font-size: 30rpx !important;
  color: #F1F5F9 !important;
  line-height: 88rpx !important;
  height: 88rpx !important;
}

.field-textarea {
  width: 100%;
  min-height: 160rpx;
  padding: 24rpx 28rpx;
  font-size: 30rpx;
  line-height: 1.6;
  color: #F1F5F9;
  background: #0F172A;
  border: 1rpx solid rgba(255, 255, 255, 0.1);
  border-radius: 16rpx;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;

  &.field-focused {
    border-color: #818CF8;
    box-shadow: 0 0 0 4rpx rgba(129, 140, 248, 0.2);
  }

  &:disabled {
    opacity: 0.5;
  }
}

/* Override uni-app default uni-textarea inner */
:deep(.uni-textarea-textarea) {
  font-size: 30rpx !important;
  color: #F1F5F9 !important;
  line-height: 1.6 !important;
}

.field-picker {
  height: 88rpx;
  padding: 0 28rpx;
  background: #0F172A;
  border: 1rpx solid rgba(255, 255, 255, 0.1);
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.picker-text {
  font-size: 30rpx;
  color: #F1F5F9;
}

.picker-placeholder {
  font-size: 28rpx;
  color: #64748B;
}

.picker-arrow {
  font-size: 24rpx;
  color: #64748B;
}

/* ===== Footer ===== */
.form-card-footer {
  padding: 16rpx 32rpx 32rpx;
}

.submit-btn {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  height: 88rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 4rpx 16rpx rgba(99, 102, 241, 0.3);

  &:active {
    transform: scale(0.97);
    opacity: 0.9;
  }
}

.submit-text {
  color: #fff;
  font-size: 32rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
}

.submitted-badge {
  background: rgba(34, 197, 94, 0.1);
  border: 1rpx solid rgba(34, 197, 94, 0.3);
  height: 80rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
}

.submitted-icon {
  font-size: 28rpx;
}

.submitted-text {
  color: #4ADE80;
  font-size: 28rpx;
  font-weight: 600;
}
</style>
