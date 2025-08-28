<script setup lang="ts">
import { ref, type PropType } from 'vue'
import { useAsyncTask } from 'vue-concurrency'

import { API } from '@/api'
import ErrorMessage from '@/components/ErrorMessage.vue'
import Loading from '@/components/LoadingItem.vue'
import type { HeaderType, BodyType } from '@/schemas'

const props = defineProps({
  header: { type: Object as PropType<HeaderType>, required: true },
  body: { type: Object as PropType<BodyType>, required: true }
})

const prompt = ref('')
const reply = ref<string>()

const sendTask = useAsyncTask<string, []>(async () => {
  return await API.chatgpt(props.header, props.body, prompt.value)
})

const send = async () => {
  reply.value = await sendTask.perform()
}
</script>

<template>
  <div class="grid gap-4">
    <h2 class="text-2xl font-bold middle">Custom Prompt</h2>
    <textarea v-model="prompt" class="textarea textarea-bordered w-full" rows="4" />
    <button class="btn btn-primary" @click="send">Send Prompt</button>
    <Loading v-if="sendTask.isRunning" />
    <ErrorMessage :error="sendTask.last?.error" v-if="sendTask.isError" />
    <div class="card border-1 border-info" v-if="reply">
      <div class="card-body">
        <h3 class="card-title text-base">Reply</h3>
        <p class="whitespace-pre-line">{{ reply }}</p>
      </div>
    </div>
  </div>
</template>
