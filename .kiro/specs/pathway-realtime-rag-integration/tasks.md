# Implementation Tasks: Pathway Real-Time Streaming RAG Integration

## Overview
This task list implements the Pathway streaming pipeline integration for QuantPulse, transforming it into a real-time financial analytics platform with RAG-powered insights for the "Hack For Green Bharat" hackathon.

## Task Breakdown

### Phase 1: Pathway Pipeline Foundation

- [x] 1. Set up Pathway development environment
  - [x] 1.1 Install Pathway framework and dependencies in backend
  - [x] 1.2 Create pathway_pipeline.py main entry point
  - [x] 1.3 Set up pathway_data/ directory structure (news/, esg/, models/)
  - [x] 1.4 Configure environment variables for Pathway (API keys, ports)

- [x] 2. Implement stock data ingestion connector
  - [x] 2.1 Create custom Python connector for yfinance polling
  - [x] 2.2 Configure watchlist of NSE stocks (RELIANCE, TCS, INFY, HDFCBANK, etc.)
  - [x] 2.3 Implement 60-second polling interval with error handling
  - [x] 2.4 Create Pathway streaming table for stock data
  - [x] 2.5 Add logging for ingestion events and errors

- [x] 3. Implement streaming technical indicators
  - [x] 3.1 Port calculate_features() logic to Pathway transformations
  - [x] 3.2 Implement RSI calculation using Pathway window operations
  - [x] 3.3 Implement MACD calculation using Pathway window operations
  - [x] 3.4 Implement Bollinger Bands calculation
  - [x] 3.5 Implement volume analysis and volatility metrics
  - [x] 3.6 Create output table with all computed indicators

### Phase 2: Document Store and RAG

- [x] 4. Set up Pathway Document Store for news
  - [x] 4.1 Configure file watcher for pathway_data/news/ directory
  - [x] 4.2 Implement document parsing for JSON news files
  - [x] 4.3 Set up text chunking with appropriate chunk size (400 tokens)
  - [x] 4.4 Configure OpenAI embeddings (or alternative embedding model)
  - [x] 4.5 Create vector index with hybrid search (semantic + BM25)
  - [x] 4.6 Test document indexing with sample news files

- [x] 5. Set up ESG/Green Score document store
  - [x] 5.1 Configure file watcher for pathway_data/esg/ directory
  - [x] 5.2 Implement ESG document parsing (PDF, TXT, JSON)
  - [x] 5.3 Create green score computation logic from ESG data
  - [x] 5.4 Index ESG documents with metadata (company, category, date)

- [x] 6. Implement RAG query engine
  - [x] 6.1 Set up LLM integration (OpenAI GPT-4 or Groq Llama)
  - [x] 6.2 Implement context retrieval from Document Store
  - [x] 6.3 Build prompt templates for financial Q&A
  - [x] 6.4 Implement citation extraction from retrieved documents
  - [x] 6.5 Add stock data enrichment to RAG context
  - [x] 6.6 Test RAG queries with sample questions

### Phase 3: Pathway REST API Server

- [x] 7. Create Pathway REST API endpoints
  - [x] 7.1 Set up FastAPI server on port 8090 within Pathway pipeline
  - [x] 7.2 Implement GET /v1/ticker/{symbol} endpoint for live features
  - [x] 7.3 Implement POST /v1/rag/query endpoint for RAG queries
  - [x] 7.4 Implement GET /v1/green-score/{symbol} endpoint
  - [x] 7.5 Implement GET /v1/status health check endpoint
  - [x] 7.6 Add CORS configuration for frontend access
  - [x] 7.7 Add request validation and error handling

### Phase 4: Data Seeding Scripts

- [x] 8. Create news seeding script
  - [x] 8.1 Implement seed_news.py using NewsAPI or Serper API
  - [x] 8.2 Configure news fetching for Indian stock market
  - [x] 8.3 Implement JSON file writing to pathway_data/news/
  - [x] 8.4 Add 2-minute polling loop for continuous news feed
  - [x] 8.5 Add error handling and rate limiting
  - [x] 8.6 Test news seeding and verify Pathway indexing

- [x] 9. Create ESG data seeding script
  - [x] 9.1 Implement seed_esg.py with realistic ESG metrics
  - [x] 9.2 Generate ESG reports for top 20 NSE stocks
  - [x] 9.3 Include categories: carbon emissions, water usage, diversity, governance
  - [x] 9.4 Write ESG data to pathway_data/esg/ directory
  - [x] 9.5 Test ESG indexing and green score computation

### Phase 5: FastAPI Backend Integration

- [ ] 10. Create Pathway proxy router
  - [ ] 10.1 Create app/routers/pathway_router.py
  - [ ] 10.2 Implement GET /api/pathway/stream/{symbol} SSE endpoint
  - [ ] 10.3 Implement POST /api/pathway/rag/query proxy endpoint
  - [ ] 10.4 Implement GET /api/pathway/green-score/{symbol} proxy endpoint
  - [ ] 10.5 Implement GET /api/pathway/status health check proxy
  - [ ] 10.6 Add connection pooling for Pathway API calls
  - [ ] 10.7 Add fallback handling when Pathway is unavailable

- [ ] 11. Integrate Pathway into existing analysis flow
  - [ ] 11.1 Modify v2_analysis.py to fetch live features from Pathway
  - [ ] 11.2 Add RAG context enrichment to analysis responses
  - [ ] 11.3 Implement graceful fallback to existing flow if Pathway unavailable
  - [ ] 11.4 Add green score to stock analysis responses

- [ ] 12. Update main.py with Pathway router
  - [ ] 12.1 Register pathway_router in FastAPI app
  - [ ] 12.2 Add startup event to verify Pathway connection
  - [ ] 12.3 Add shutdown event for cleanup
  - [ ] 12.4 Update API documentation with new endpoints

### Phase 6: Frontend Integration

- [ ] 13. Update API client for Pathway endpoints
  - [ ] 13.1 Add connectToStream(symbol) SSE connection in api.ts
  - [ ] 13.2 Add queryRAG(question) function in api.ts
  - [ ] 13.3 Add fetchGreenScore(symbol) function in api.ts
  - [ ] 13.4 Add fetchPathwayStatus() health check function
  - [ ] 13.5 Implement error handling and retry logic

- [ ] 14. Create LiveStreamIndicator component
  - [ ] 14.1 Create LiveStreamIndicator.tsx component
  - [ ] 14.2 Implement pulsing green dot animation
  - [ ] 14.3 Show connection status (connected/disconnected/error)
  - [ ] 14.4 Display last update timestamp
  - [ ] 14.5 Add reconnection logic on disconnect

- [ ] 15. Create RAG Query Panel component
  - [ ] 15.1 Create RAGQueryPanel.tsx chat-style component
  - [ ] 15.2 Implement message input and send functionality
  - [ ] 15.3 Display AI responses with source citations
  - [ ] 15.4 Add loading states and error handling
  - [ ] 15.5 Implement conversation history display
  - [ ] 15.6 Add example questions for user guidance

- [ ] 16. Create Green Score Badge component
  - [ ] 16.1 Create GreenScoreBadge.tsx component
  - [ ] 16.2 Design leaf icon with score display
  - [ ] 16.3 Implement color coding (green/yellow/red)
  - [ ] 16.4 Add tooltip with ESG breakdown
  - [ ] 16.5 Add loading and error states

- [ ] 17. Update Dashboard with live features
  - [ ] 17.1 Add LiveStreamIndicator to dashboard header
  - [ ] 17.2 Add GreenScoreBadge next to stock names
  - [ ] 17.3 Add RAGQueryPanel as collapsible side panel
  - [ ] 17.4 Wire up SSE for auto-updating price displays
  - [ ] 17.5 Wire up SSE for auto-updating indicators
  - [ ] 17.6 Add manual refresh button as fallback

### Phase 7: Testing and Validation

- [x] 18. Test Pathway pipeline functionality
  - [x] 18.1 Verify stock data ingestion from yfinance
  - [x] 18.2 Verify technical indicators computation accuracy
  - [x] 18.3 Verify news document indexing and search
  - [x] 18.4 Verify ESG document indexing and green score
  - [x] 18.5 Verify RAG query responses with citations
  - [x] 18.6 Test REST API endpoints (all /v1/* routes)

- [ ] 19. Test FastAPI integration
  - [ ] 19.1 Test SSE streaming endpoint with multiple clients
  - [ ] 19.2 Test RAG proxy endpoint with various questions
  - [ ] 19.3 Test green score proxy endpoint
  - [ ] 19.4 Test fallback behavior when Pathway is down
  - [ ] 19.5 Test concurrent requests and load handling

- [ ] 20. Test frontend integration
  - [ ] 20.1 Test live stream connection and auto-updates
  - [ ] 20.2 Test RAG query panel with various questions
  - [ ] 20.3 Test green score badge display
  - [ ] 20.4 Test reconnection logic on network issues
  - [ ] 20.5 Test responsive design on mobile devices

- [ ] 21. End-to-end integration testing
  - [ ] 21.1 Test complete flow: news seeding → indexing → RAG query
  - [ ] 21.2 Test complete flow: stock data → indicators → SSE → frontend
  - [ ] 21.3 Test complete flow: ESG data → green score → badge display
  - [ ] 21.4 Test system behavior under load (50 stocks, 100 clients)
  - [ ] 21.5 Test error recovery scenarios

### Phase 8: Documentation and Deployment

- [ ] 22. Create deployment documentation
  - [ ] 22.1 Document Pathway pipeline setup and configuration
  - [ ] 22.2 Document environment variables and API keys required
  - [ ] 22.3 Create startup scripts for development and production
  - [ ] 22.4 Document data seeding process
  - [ ] 22.5 Create troubleshooting guide for common issues

- [ ] 23. Create user documentation
  - [ ] 23.1 Document RAG query panel usage with examples
  - [ ] 23.2 Document green score interpretation
  - [ ] 23.3 Document live streaming features
  - [ ] 23.4 Create demo video showing all features

- [ ] 24. Prepare for hackathon demo
  - [ ] 24.1 Seed sufficient news and ESG data for demo
  - [ ] 24.2 Configure watchlist with diverse stocks
  - [ ] 24.3 Prepare demo script highlighting Pathway features
  - [ ] 24.4 Test complete system on clean environment
  - [ ] 24.5 Create presentation slides with architecture diagrams

### Phase 9: Hackathon-Specific Requirements

- [ ] 25. Demonstrate Pathway connector usage
  - [ ] 25.1 Document custom Python connector implementation
  - [ ] 25.2 Show live data ingestion in action
  - [ ] 25.3 Demonstrate fallback to demo mode if needed

- [ ] 26. Demonstrate streaming transformations
  - [ ] 26.1 Show incremental indicator computation
  - [ ] 26.2 Demonstrate window operations for technical analysis
  - [ ] 26.3 Show real-time feature engineering pipeline

- [ ] 27. Demonstrate LLM integration
  - [ ] 27.1 Show RAG queries with live market context
  - [ ] 27.2 Demonstrate citation and source attribution
  - [ ] 27.3 Show explainable insights generation

- [ ] 28. Performance optimization
  - [ ] 28.1 Optimize document chunking and embedding
  - [ ] 28.2 Optimize vector search performance
  - [ ] 28.3 Optimize SSE broadcasting efficiency
  - [ ] 28.4 Add caching where appropriate
  - [ ] 28.5 Profile and optimize bottlenecks

### Phase 10: Polish and Final Touches

- [ ] 29. UI/UX improvements
  - [ ] 29.1 Add smooth animations for live updates
  - [ ] 29.2 Improve loading states and skeleton screens
  - [ ] 29.3 Add toast notifications for important events
  - [ ] 29.4 Improve mobile responsiveness
  - [ ] 29.5 Add dark mode support for new components

- [ ] 30. Error handling and resilience
  - [ ] 30.1 Add comprehensive error messages
  - [ ] 30.2 Implement retry logic with exponential backoff
  - [ ] 30.3 Add circuit breaker for external APIs
  - [ ] 30.4 Implement graceful degradation
  - [ ] 30.5 Add monitoring and alerting

## Success Criteria

### Functional Requirements
- ✅ Pathway pipeline ingests live stock data every 60 seconds
- ✅ Technical indicators computed in real-time using streaming transformations
- ✅ News and ESG documents automatically indexed when added
- ✅ RAG queries return relevant answers with citations
- ✅ Green scores computed from ESG data
- ✅ SSE streaming works with multiple concurrent clients
- ✅ Frontend displays live updates without manual refresh

### Hackathon Requirements
- ✅ Live data ingestion using Pathway connectors (custom Python connector)
- ✅ Streaming transformations for feature engineering (window operations)
- ✅ LLM integration for real-time insights (RAG with Document Store)
- ✅ Modular architecture with clear separation of concerns
- ✅ Production-ready error handling and resilience

### Performance Targets
- Stock data ingestion latency: < 2 seconds
- Indicator computation latency: < 1 second
- Document indexing latency: < 30 seconds
- RAG query response time: < 5 seconds
- SSE update broadcast: < 1 second
- Support 50+ stocks and 100+ concurrent clients

## Notes

- All Pathway-related code should be in `QuantPulse-Backend/pathway_pipeline.py` and `QuantPulse-Backend/pathway_data/`
- FastAPI integration should be minimal and non-invasive to existing code
- Frontend components should be reusable and follow existing design patterns
- Focus on demonstrating Pathway's unique capabilities for the hackathon
- Ensure system works in demo mode without requiring paid API keys
