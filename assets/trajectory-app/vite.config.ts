import react from '@vitejs/plugin-react'
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { defineConfig } from 'vite'

const dataFile = process.env.TRAJECTORY_DATA_FILE
  ? resolve(process.env.TRAJECTORY_DATA_FILE)
  : resolve(process.cwd(), 'data/places.json')
const instanceToken = process.env.TRAJECTORY_INSTANCE_TOKEN ?? 'manual-start'

async function readPlaces() {
  const content = await readFile(dataFile, 'utf8')
  return JSON.parse(content)
}

async function writePlaces(places: unknown[]) {
  await mkdir(dirname(dataFile), { recursive: true })
  const temporaryFile = `${dataFile}.tmp`
  await writeFile(temporaryFile, `${JSON.stringify(places, null, 2)}\n`, 'utf8')
  await rename(temporaryFile, dataFile)
}

function sendJson(response: ServerResponse, status: number, body: unknown) {
  response.statusCode = status
  response.setHeader('Content-Type', 'application/json; charset=utf-8')
  response.end(JSON.stringify(body))
}

async function placesHandler(request: IncomingMessage, response: ServerResponse) {
  try {
    if (request.method === 'GET') {
      response.setHeader('X-Trajectory-Instance', instanceToken)
      sendJson(response, 200, await readPlaces())
      return
    }

    if (request.method === 'PUT') {
      const chunks: Buffer[] = []
      for await (const chunk of request) chunks.push(Buffer.from(chunk))
      const places = JSON.parse(Buffer.concat(chunks).toString('utf8'))
      if (!Array.isArray(places)) {
        sendJson(response, 400, { message: '节点数据必须是数组' })
        return
      }
      await writePlaces(places)
      sendJson(response, 200, { saved: true, count: places.length })
      return
    }

    sendJson(response, 405, { message: '不支持的请求方式' })
  } catch (error) {
    console.error('places.json read/write failed:', error)
    sendJson(response, 500, { message: '本地数据读写失败' })
  }
}

function localPlacesApi() {
  const attach = (middlewares: { use: (path: string, handler: typeof placesHandler) => void }) => {
    middlewares.use('/api/places', placesHandler)
  }

  return {
    name: 'local-places-api',
    configureServer(server: { middlewares: Parameters<typeof attach>[0] }) {
      attach(server.middlewares)
    },
    configurePreviewServer(server: { middlewares: Parameters<typeof attach>[0] }) {
      attach(server.middlewares)
    },
  }
}

export default defineConfig({
  plugins: [react(), localPlacesApi()],
})
