import { Injectable, Logger } from '@nestjs/common'
import { ConfigService } from '@nestjs/config'
import axios from 'axios'
import FormData from 'form-data'

@Injectable()
export class OcrService {
	private readonly logger = new Logger(OcrService.name)

	constructor(private readonly configService: ConfigService) {}

	async extractText(imageBuffer: Buffer): Promise<string> {
		const ocrBaseUrl = this.configService.get<string>('OCR_SERVICE_URL')
		if (!ocrBaseUrl) {
			throw new Error('OCR_SERVICE_URL is not configured')
		}

		const formData = new FormData()
		formData.append('file', imageBuffer, {
			filename: 'receipt.jpg',
			contentType: 'image/jpeg',
		})

		const headers = formData.getHeaders()

		const response = await axios.post<{ text?: string }>(`${ocrBaseUrl}/ocr`, formData, {
			headers,
			timeout: 30000,
		})

		const extractedText = response.data?.text?.trim() ?? ''
		this.logger.debug(`OCR returned text length=${extractedText.length}`)
		return extractedText
	}
}
