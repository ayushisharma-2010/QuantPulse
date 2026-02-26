# Requirements Document: Pathway Real-Time Streaming RAG Integration

## Introduction

This document specifies the requirements for integrating Pathway real-time streaming framework into the QuantPulse stock analytics platform for the "Hack For Green Bharat" hackathon. The integration transforms QuantPulse from a cached API-based system into a real-time streaming analytics platform with RAG-powered financial intelligence.

The system will ingest live stock market data through Pathway connectors, compute technical indicators using streaming transformations, implement a RAG-powered financial Q&A system using Pathway's Document Store, and detect market anomalies with LLM-generated explanations.

## Glossary

- **Pathway**: A Python framework for real-time data processing and streaming analytics
- **Pathway_Connector**: A component that ingests data from external sources into Pathway streaming pipelines
- **Pathway_Table**: An immutable, versioned data structure representing streaming data in Pathway
- **Streaming_Pipeline**: A Pathway computation graph that processes data incrementally as it arrives
- **Document_Store**: Pathway's vector database for live document indexing and semantic search
- **RAG**: Retrieval-Augmented Generation - combining semantic search with LLM generation
- **LLM_xPack**: Pathway's extension package for LLM integration and RAG workflows
- **Technical_Indicator**: Mathematical calculations on stock data (RSI, MACD, Bollinger Bands, Moving Averages)
- **Window_Operation**: Time-based or count-based aggregations over streaming data
- **Incremental_Join**: A streaming join operation that updates results as new data arrives
- **Market_Anomaly**: Unusual patterns in stock data (price spikes, volume surges, volatility changes)
- **Stock_Provider**: External API service providing market data (TwelveData, Finnhub)
- **WebSocket**: Bidirectional communication protocol for real-time frontend updates
- **FastAPI_Backend**: The existing QuantPulse Python backend using FastAPI framework
- **NSE**: National Stock Exchange of India

## Requirements

### Requirement 1: Real-Time Market Data Ingestion

**User Story:** As a trader, I want to receive live stock market data in real-time, so that I can make timely trading decisions based on current market conditions.

#### Acceptance Criteria

1. THE Pathway_Connector SHALL ingest stock data from TwelveData API or Finnhub API at configurable intervals
2. WHEN live API data is unavailable, THE Pathway_Connector SHALL fall back to Pathway demo module for simulated streaming data
3. THE Streaming_Pipeline SHALL process stock symbols configured in the system (minimum 10 NSE stocks)
4. WHEN new market data arrives, THE Pathway_Table SHALL update within 2 seconds of data availability
5. THE Pathway_Connector SHALL handle API rate limits by queuing requests and respecting provider constraints
6. WHEN API errors occur, THE Pathway_Connector SHALL log errors and continue processing other symbols without pipeline failure
7. THE Streaming_Pipeline SHALL persist the last 24 hours of streaming data for historical queries

### Requirement 2: Streaming Technical Indicator Computation

**User Story:** As a technical analyst, I want real-time technical indicators computed on streaming data, so that I can identify trading signals as they emerge.

#### Acceptance Criteria

1. THE Streaming_Pipeline SHALL compute RSI (Relative Strength Index) using 14-period windows on streaming price data
2. THE Streaming_Pipeline SHALL compute MACD (Moving Average Convergence Divergence) using 12-period and 26-period exponential moving averages
3. THE Streaming_Pipeline SHALL compute Bollinger Bands using 20-period moving average and 2 standard deviations
4. THE Streaming_Pipeline SHALL compute Simple Moving Averages for 20-period, 50-period, and 200-period windows
5. WHEN new price data arrives, THE Streaming_Pipeline SHALL update all technical indicators incrementally within 1 second
6. THE Streaming_Pipeline SHALL use Pathway window operations for rolling calculations to maintain computational efficiency
7. THE Streaming_Pipeline SHALL expose computed indicators through FastAPI endpoints for frontend consumption
8. WHEN insufficient data exists for indicator calculation, THE Streaming_Pipeline SHALL return null values with appropriate status messages

### Requirement 3: Live RAG Document Store for Financial Intelligence

**User Story:** As an investor, I want to query financial news and reports in natural language, so that I can quickly understand market context without manual research.

#### Acceptance Criteria

1. THE Document_Store SHALL index financial news articles from configured news sources
2. THE Document_Store SHALL index company reports and market analysis documents in PDF and text formats
3. WHEN new documents are added to monitored directories, THE Document_Store SHALL automatically index them within 30 seconds
4. THE Document_Store SHALL use hybrid retrieval combining semantic search (embeddings) and BM25 keyword search
5. THE Document_Store SHALL maintain live vector indices that update incrementally as documents arrive
6. WHEN a document is indexed, THE Document_Store SHALL extract metadata including timestamp, source, and stock symbols mentioned
7. THE Document_Store SHALL support queries filtered by date range, stock symbol, and document type
8. THE Document_Store SHALL return top 5 most relevant document chunks for each retrieval query

### Requirement 4: LLM-Powered Financial Q&A System

**User Story:** As a portfolio manager, I want to ask questions about market conditions in natural language, so that I can get instant insights combining live data and financial knowledge.

#### Acceptance Criteria

1. WHEN a user submits a natural language query, THE LLM_xPack SHALL retrieve relevant context from Document_Store and streaming data
2. THE LLM_xPack SHALL generate responses using an LLM (OpenAI GPT-4, Anthropic Claude, or Groq Llama) with retrieved context
3. THE LLM_xPack SHALL include citations referencing source documents and data timestamps in responses
4. WHEN a query mentions specific stock symbols, THE LLM_xPack SHALL include current streaming data for those symbols in context
5. THE LLM_xPack SHALL handle queries about price movements, technical indicators, news sentiment, and market trends
6. WHEN the LLM cannot answer with available context, THE LLM_xPack SHALL explicitly state information limitations
7. THE LLM_xPack SHALL respond to queries within 5 seconds for 95% of requests
8. THE LLM_xPack SHALL support conversation history for follow-up questions within a session

### Requirement 5: Real-Time Market Anomaly Detection

**User Story:** As a risk manager, I want to be alerted to unusual market activity in real-time, so that I can respond quickly to potential risks or opportunities.

#### Acceptance Criteria

1. THE Streaming_Pipeline SHALL detect price movements exceeding 5% within a 5-minute window
2. THE Streaming_Pipeline SHALL detect volume spikes exceeding 3x the 20-period moving average
3. THE Streaming_Pipeline SHALL detect volatility changes when standard deviation exceeds 2x the 50-period average
4. WHEN an anomaly is detected, THE Streaming_Pipeline SHALL generate an alert event within 2 seconds
5. WHEN an anomaly alert is generated, THE LLM_xPack SHALL create a natural language explanation combining market data and news context
6. THE Streaming_Pipeline SHALL deduplicate alerts to prevent repeated notifications for the same anomaly within 15 minutes
7. THE Streaming_Pipeline SHALL classify anomalies by severity (low, medium, high) based on magnitude and market impact
8. THE Streaming_Pipeline SHALL expose anomaly alerts through WebSocket connections for real-time frontend notifications

### Requirement 6: FastAPI Integration and REST Endpoints

**User Story:** As a frontend developer, I want well-defined REST APIs for streaming data and RAG queries, so that I can build responsive user interfaces.

#### Acceptance Criteria

1. THE FastAPI_Backend SHALL expose endpoint `/api/v1/streaming/stocks/{symbol}/live` for current streaming data
2. THE FastAPI_Backend SHALL expose endpoint `/api/v1/streaming/indicators/{symbol}` for real-time technical indicators
3. THE FastAPI_Backend SHALL expose endpoint `/api/v1/rag/query` accepting POST requests with natural language questions
4. THE FastAPI_Backend SHALL expose endpoint `/api/v1/streaming/anomalies` for recent anomaly alerts
5. THE FastAPI_Backend SHALL expose endpoint `/api/v1/streaming/status` for Pathway pipeline health and statistics
6. WHEN streaming data is requested, THE FastAPI_Backend SHALL return data from Pathway_Table with timestamps and metadata
7. THE FastAPI_Backend SHALL implement request validation using Pydantic schemas for all endpoints
8. THE FastAPI_Backend SHALL return appropriate HTTP status codes (200, 400, 404, 500) with descriptive error messages

### Requirement 7: WebSocket Support for Real-Time Updates

**User Story:** As a day trader, I want live updates pushed to my screen automatically, so that I don't need to refresh the page to see new data.

#### Acceptance Criteria

1. THE FastAPI_Backend SHALL provide WebSocket endpoint `/ws/streaming/stocks` for live stock data subscriptions
2. WHEN a client subscribes to a stock symbol via WebSocket, THE FastAPI_Backend SHALL push updates whenever Pathway_Table changes
3. THE FastAPI_Backend SHALL support multiple concurrent WebSocket connections (minimum 100 clients)
4. WHEN an anomaly is detected, THE FastAPI_Backend SHALL broadcast alerts to all subscribed WebSocket clients within 1 second
5. THE FastAPI_Backend SHALL implement WebSocket heartbeat messages every 30 seconds to maintain connections
6. WHEN a WebSocket connection fails, THE FastAPI_Backend SHALL clean up resources and log disconnection events
7. THE FastAPI_Backend SHALL allow clients to subscribe to multiple stock symbols on a single WebSocket connection
8. THE FastAPI_Backend SHALL send updates in JSON format with schema version for backward compatibility

### Requirement 8: Configuration and Deployment

**User Story:** As a DevOps engineer, I want configurable deployment options, so that I can run the system in development, demo, and production environments.

#### Acceptance Criteria

1. THE Streaming_Pipeline SHALL read configuration from environment variables and configuration files
2. THE Streaming_Pipeline SHALL support three modes: live (real APIs), demo (simulated data), and hybrid (fallback)
3. WHEN running in demo mode, THE Streaming_Pipeline SHALL use Pathway demo module to generate realistic market data
4. THE Streaming_Pipeline SHALL validate required API keys on startup and log configuration status
5. THE Streaming_Pipeline SHALL expose configuration endpoint `/api/v1/streaming/config` showing active mode and data sources
6. THE Streaming_Pipeline SHALL support graceful shutdown, completing in-flight requests before terminating
7. THE Streaming_Pipeline SHALL log startup time, pipeline initialization, and first data ingestion timestamp
8. THE Streaming_Pipeline SHALL include health check endpoint returning pipeline status, uptime, and error counts

### Requirement 9: Error Handling and Resilience

**User Story:** As a system administrator, I want robust error handling, so that temporary failures don't crash the entire system.

#### Acceptance Criteria

1. WHEN a Stock_Provider API call fails, THE Pathway_Connector SHALL retry up to 3 times with exponential backoff
2. WHEN all retries fail, THE Pathway_Connector SHALL log the error and continue processing other symbols
3. WHEN the Document_Store encounters indexing errors, THE Document_Store SHALL log the error and skip the problematic document
4. WHEN the LLM_xPack encounters API errors, THE LLM_xPack SHALL return a fallback response indicating service unavailability
5. THE Streaming_Pipeline SHALL implement circuit breaker pattern for external API calls with 5-minute cooldown
6. WHEN memory usage exceeds 80%, THE Streaming_Pipeline SHALL trigger garbage collection and log memory warnings
7. THE Streaming_Pipeline SHALL persist critical state to disk every 5 minutes for recovery after crashes
8. THE Streaming_Pipeline SHALL include error metrics in health check endpoint (error rate, last error timestamp)

### Requirement 10: Performance and Scalability

**User Story:** As a product manager, I want the system to handle growing data volumes efficiently, so that we can scale to more users and stocks.

#### Acceptance Criteria

1. THE Streaming_Pipeline SHALL process updates for 50 stock symbols with sub-second latency
2. THE Streaming_Pipeline SHALL handle 1000 document indexing operations per minute without degradation
3. THE Document_Store SHALL support vector search queries with response time under 200ms for 95th percentile
4. THE Streaming_Pipeline SHALL use incremental computation to avoid reprocessing unchanged data
5. THE Streaming_Pipeline SHALL implement backpressure handling when data ingestion rate exceeds processing capacity
6. THE Streaming_Pipeline SHALL use connection pooling for external API calls to minimize overhead
7. THE Streaming_Pipeline SHALL expose performance metrics (throughput, latency, queue depth) via monitoring endpoint
8. THE Streaming_Pipeline SHALL support horizontal scaling by partitioning stock symbols across multiple pipeline instances

### Requirement 11: Testing and Validation

**User Story:** As a quality assurance engineer, I want comprehensive testing capabilities, so that I can verify system correctness before production deployment.

#### Acceptance Criteria

1. THE Streaming_Pipeline SHALL include unit tests for all technical indicator calculations with known input/output pairs
2. THE Streaming_Pipeline SHALL include integration tests using Pathway demo module for end-to-end validation
3. THE Streaming_Pipeline SHALL include property-based tests for streaming transformations verifying incremental correctness
4. THE Document_Store SHALL include tests verifying retrieval quality using sample financial documents
5. THE LLM_xPack SHALL include tests with mocked LLM responses to validate RAG pipeline logic
6. THE Streaming_Pipeline SHALL include load tests simulating 100 concurrent users and 50 stock symbols
7. THE Streaming_Pipeline SHALL include chaos tests simulating API failures, network errors, and resource exhaustion
8. THE Streaming_Pipeline SHALL achieve minimum 80% code coverage for core streaming logic

### Requirement 12: Documentation and Observability

**User Story:** As a developer joining the project, I want clear documentation and observability, so that I can understand and debug the system quickly.

#### Acceptance Criteria

1. THE Streaming_Pipeline SHALL include inline code documentation for all public functions and classes
2. THE Streaming_Pipeline SHALL include architecture diagram showing data flow from ingestion to output
3. THE Streaming_Pipeline SHALL include API documentation using OpenAPI/Swagger for all endpoints
4. THE Streaming_Pipeline SHALL log all pipeline stages (ingestion, transformation, output) with structured logging
5. THE Streaming_Pipeline SHALL include example queries and expected responses in documentation
6. THE Streaming_Pipeline SHALL expose metrics endpoint `/api/v1/streaming/metrics` in Prometheus format
7. THE Streaming_Pipeline SHALL include troubleshooting guide for common errors and configuration issues
8. THE Streaming_Pipeline SHALL include README with quickstart instructions for local development and demo mode
