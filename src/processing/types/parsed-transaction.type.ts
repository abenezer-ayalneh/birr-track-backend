export type ParsedTransaction = {
	bankName: string | null
	amount: number | null
	transactionId: string | null
	timestamp: string | null
	confidence: number
	usedLlm: boolean
}
