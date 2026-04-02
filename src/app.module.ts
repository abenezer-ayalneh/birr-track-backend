import { Logger, Module } from '@nestjs/common'
import { ConfigModule, ConfigService } from '@nestjs/config'
import { APP_FILTER, APP_GUARD } from '@nestjs/core'
import { ThrottlerGuard, ThrottlerModule } from '@nestjs/throttler'

import AppController from './app.controller'
import AppService from './app.service'
import GlobalExceptionFilter from './shared/filters/global-exception.filter'

@Module({
	imports: [
		ConfigModule.forRoot({ isGlobal: true, expandVariables: true }),
		ThrottlerModule.forRootAsync({
			imports: [ConfigModule],
			inject: [ConfigService],
			useFactory: (config: ConfigService) => [
				{
					ttl: config.get('THROTTLER_TTL'), // The number of milliseconds that each request will last in storage
					limit: config.get('THROTTLER_LIMIT'), // The maximum number of requests within the TTL limit
				},
			],
		}),
	],
	controllers: [AppController],
	providers: [
		AppService,
		Logger,
		{
			provide: APP_GUARD,
			useClass: ThrottlerGuard,
		},
		{ provide: APP_FILTER, useClass: GlobalExceptionFilter },
	],
})
export default class AppModule {}
