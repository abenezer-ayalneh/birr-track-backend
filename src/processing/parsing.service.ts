import { Injectable } from '@nestjs/common'

import { LlmService } from './llm.service'
import { ParsedTransaction } from './types/parsed-transaction.type'

const BANK_NAMES = ['CBE', 'Commercial Bank of Ethiopia', 'Awash', 'Abyssinia', 'Dashen', 'Hibret', 'Telebirr']

/** English month names for OCR'd receipts (abbreviated or full). */
const MONTH_NAME_PATTERN =
	'Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?'

@Injectable()
export class ParsingService {
	constructor(private readonly llmService: LlmService) {}

	async parse(ocrText: string): Promise<ParsedTransaction> {
		const regexParsed = this.parseWithRegex(ocrText)

		const hasCriticalFields =
			regexParsed.amount !== null && regexParsed.transactionId !== null && regexParsed.timestamp !== null && regexParsed.bankName !== null

		if (hasCriticalFields) {
			return {
				...regexParsed,
				confidence: 0.92,
				usedLlm: false,
			}
		}

		const llmParsed = await this.llmService.extractFields(ocrText)
		const merged: ParsedTransaction = {
			bankName: regexParsed.bankName ?? llmParsed.bankName,
			amount: regexParsed.amount ?? llmParsed.amount,
			transactionId: regexParsed.transactionId ?? llmParsed.transactionId,
			timestamp: regexParsed.timestamp ?? llmParsed.timestamp,
			usedLlm: true,
			confidence: 0.78,
		}

		const mergedHasAllFields = merged.amount !== null && merged.transactionId !== null && merged.timestamp !== null && merged.bankName !== null

		if (!mergedHasAllFields) {
			return { ...merged, confidence: 0.55 }
		}

		return merged
	}

	private parseWithRegex(ocrText: string): Omit<ParsedTransaction, 'confidence' | 'usedLlm'> {
		const amountRegex = /(?:ETB|Birr|Br)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})|[0-9]+(?:\.[0-9]{1,2}))/i
		const transactionIdRegex = /(?:tx(?:n|id)?|transaction(?:\s*id)?|reference|ref)[\s:#-]*([A-Za-z0-9-]{6,})/i

		const amountMatch = ocrText.match(amountRegex)
		const transactionIdMatch = ocrText.match(transactionIdRegex)

		const amount = amountMatch ? Number(amountMatch[1].replaceAll(',', '')) : null
		const transactionId = transactionIdMatch ? transactionIdMatch[1] : null
		const timestamp = this.extractTimestampFromText(ocrText)
		const bankName = this.extractBankName(ocrText)

		return {
			amount: Number.isFinite(amount) ? amount : null,
			transactionId,
			timestamp,
			bankName,
		}
	}

	/**
	 * First valid date wins. Supports common receipt formats: DD-Mon-YYYY, YYYY-MM-DD,
	 * numeric D/M/Y and M/D/Y (heuristic when ambiguous), and month-first English phrases.
	 */
	private extractTimestampFromText(ocrText: string): string | null {
		return (
			this.tryParseDayMonthNameYear(ocrText) ??
			this.tryParseMonthNameDayYear(ocrText) ??
			this.tryParseYearMonthDay(ocrText) ??
			this.tryParseNumericDelimitedDate(ocrText)
		)
	}

	private tryParseDayMonthNameYear(text: string): string | null {
		const re = new RegExp(String.raw`\b(\d{1,2})[-/.](${MONTH_NAME_PATTERN})[-/.](\d{4})\b`, 'i')
		const m = text.match(re)
		if (!m) {
			return null
		}
		const day = Number.parseInt(m[1], 10)
		const monthIndex = this.monthNameToIndex(m[2])
		const year = Number.parseInt(m[3], 10)
		if (monthIndex === null || !this.isReasonableYMD(year, monthIndex, day)) {
			return null
		}
		return this.toIsoUtcMidnight(year, monthIndex, day)
	}

	private tryParseMonthNameDayYear(text: string): string | null {
		const re = new RegExp(String.raw`\b(${MONTH_NAME_PATTERN})[-/.]?\s+(\d{1,2})(?:st|nd|rd|th)?[,/\s]+(\d{4})\b`, 'i')
		const m = text.match(re)
		if (!m) {
			return null
		}
		const monthIndex = this.monthNameToIndex(m[1])
		const day = Number.parseInt(m[2], 10)
		const year = Number.parseInt(m[3], 10)
		if (monthIndex === null || !this.isReasonableYMD(year, monthIndex, day)) {
			return null
		}
		return this.toIsoUtcMidnight(year, monthIndex, day)
	}

	private tryParseYearMonthDay(text: string): string | null {
		const re = /\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[T\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?\b/
		const m = text.match(re)
		if (!m) {
			return null
		}
		const year = Number.parseInt(m[1], 10)
		const month = Number.parseInt(m[2], 10) - 1
		const day = Number.parseInt(m[3], 10)
		if (!this.isReasonableYMD(year, month, day)) {
			return null
		}
		if (m[4] !== undefined && m[5] !== undefined) {
			const h = Number.parseInt(m[4], 10)
			const min = Number.parseInt(m[5], 10)
			const s = m[6] !== undefined ? Number.parseInt(m[6], 10) : 0
			if (h < 0 || h > 23 || min < 0 || min > 59 || s < 0 || s > 59) {
				return null
			}
			const d = new Date(Date.UTC(year, month, day, h, min, s))
			return Number.isNaN(d.getTime()) ? null : d.toISOString()
		}
		return this.toIsoUtcMidnight(year, month, day)
	}

	/**
	 * DD/MM/YYYY or MM/DD/YYYY (also - or .). If one part > 12, interpret unambiguously.
	 * If both ≤ 12, prefer day-first (common outside US, including many bank SMS/receipts).
	 */
	private tryParseNumericDelimitedDate(text: string): string | null {
		const re = /\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?\b/
		const m = text.match(re)
		if (!m) {
			return null
		}
		const a = Number.parseInt(m[1], 10)
		const b = Number.parseInt(m[2], 10)
		const year = Number.parseInt(m[3], 10)

		let monthIndex: number
		let day: number

		if (a > 12) {
			day = a
			monthIndex = b - 1
		} else if (b > 12) {
			monthIndex = a - 1
			day = b
		} else {
			day = a
			monthIndex = b - 1
		}

		if (!this.isReasonableYMD(year, monthIndex, day)) {
			return null
		}

		if (m[4] !== undefined && m[5] !== undefined) {
			const h = Number.parseInt(m[4], 10)
			const min = Number.parseInt(m[5], 10)
			const s = m[6] !== undefined ? Number.parseInt(m[6], 10) : 0
			if (h < 0 || h > 23 || min < 0 || min > 59 || s < 0 || s > 59) {
				return null
			}
			const d = new Date(Date.UTC(year, monthIndex, day, h, min, s))
			return Number.isNaN(d.getTime()) ? null : d.toISOString()
		}

		return this.toIsoUtcMidnight(year, monthIndex, day)
	}

	private monthNameToIndex(raw: string): number | null {
		const key = raw.toLowerCase().replace(/\./g, '').slice(0, 3)
		const map: Record<string, number> = {
			jan: 0,
			feb: 1,
			mar: 2,
			apr: 3,
			may: 4,
			jun: 5,
			jul: 6,
			aug: 7,
			sep: 8,
			oct: 9,
			nov: 10,
			dec: 11,
		}
		const idx = map[key]
		return idx === undefined ? null : idx
	}

	private isReasonableYMD(year: number, monthIndex: number, day: number): boolean {
		if (year < 1970 || year > 2100 || monthIndex < 0 || monthIndex > 11 || day < 1 || day > 31) {
			return false
		}
		const d = new Date(Date.UTC(year, monthIndex, day))
		return d.getUTCFullYear() === year && d.getUTCMonth() === monthIndex && d.getUTCDate() === day
	}

	private toIsoUtcMidnight(year: number, monthIndex: number, day: number): string | null {
		const d = new Date(Date.UTC(year, monthIndex, day))
		return Number.isNaN(d.getTime()) ? null : d.toISOString()
	}

	private extractBankName(ocrText: string): string | null {
		const normalizedText = ocrText.toLowerCase()
		const matched = BANK_NAMES.find((bank) => normalizedText.includes(bank.toLowerCase()))
		return matched ?? null
	}
}
