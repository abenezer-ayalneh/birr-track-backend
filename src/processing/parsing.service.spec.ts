import { Test, TestingModule } from '@nestjs/testing'

import { LlmService } from './llm.service'
import { ParsingService } from './parsing.service'

describe('ParsingService', () => {
	let service: ParsingService
	let llmExtractFields: jest.Mock

	beforeEach(async () => {
		llmExtractFields = jest.fn().mockResolvedValue({
			bankName: null,
			amount: null,
			transactionId: null,
			timestamp: null,
		})

		const module: TestingModule = await Test.createTestingModule({
			providers: [
				ParsingService,
				{
					provide: LlmService,
					useValue: { extractFields: llmExtractFields },
				},
			],
		}).compile()

		service = module.get(ParsingService)
	})

	it('parses DD-Mon-YYYY (CBE receipt style) without LLM', async () => {
		const text = `ETB 100.00 on 04-Apr-2026 with transactionID:FT26094X0XVY
Commercial Bank of Ethiopia`
		const result = await service.parse(text)
		expect(result.usedLlm).toBe(false)
		expect(result.timestamp).toBe('2026-04-04T00:00:00.000Z')
		expect(llmExtractFields).not.toHaveBeenCalled()
	})

	it('parses YYYY-MM-DD with optional time', async () => {
		const text = `ETB 50.00 on 2026-04-08 14:30:00 transaction ref ABC123XY
Commercial Bank of Ethiopia`
		const result = await service.parse(text)
		expect(result.usedLlm).toBe(false)
		expect(result.timestamp).toBe('2026-04-08T14:30:00.000Z')
	})

	it('parses numeric DD/MM/YYYY when day > 12', async () => {
		const text = `ETB 10.00 15/03/2026 ref TX999999999
Commercial Bank of Ethiopia`
		const result = await service.parse(text)
		expect(result.usedLlm).toBe(false)
		expect(result.timestamp).toBe('2026-03-15T00:00:00.000Z')
	})

	it('parses US-style MM/DD/YYYY when day > 12', async () => {
		const text = `ETB 10.00 03/15/2026 ref TX999999999
Commercial Bank of Ethiopia`
		const result = await service.parse(text)
		expect(result.usedLlm).toBe(false)
		expect(result.timestamp).toBe('2026-03-15T00:00:00.000Z')
	})

	it('parses Month D, YYYY', async () => {
		const text = `ETB 1.00 on April 8, 2026 transaction id REF123456789
Commercial Bank of Ethiopia`
		const result = await service.parse(text)
		expect(result.usedLlm).toBe(false)
		expect(result.timestamp).toBe('2026-04-08T00:00:00.000Z')
	})
})
