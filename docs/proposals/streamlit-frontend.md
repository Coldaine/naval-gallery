# ADR-006: Streamlit Frontend for Naval Gallery

## Context

The Naval Gallery project currently uses a simple HTML/JavaScript frontend that works well for viewing and filtering curated naval technical drawings. However, as the project incorporates AI vision capabilities for automated classification and analysis, there's a need for a more sophisticated GUI interface that can:

- Display AI analysis results alongside images
- Provide tools for manual review and correction of AI classifications
- Offer enhanced image management capabilities
- Support the curation workflow with a proper GUI instead of CLI tools

## Decision

Implement a Streamlit-based GUI frontend to complement the existing HTML gallery, focusing on the curation and analysis workflow aspects of the project.

## Rationale

### Why Streamlit?
- **Rapid Development**: Streamlit allows for quick prototyping and development of data-focused applications
- **AI/ML Integration**: Native support for displaying model outputs, which is perfect for our vision classification results
- **Image Handling**: Excellent built-in support for displaying images with metadata
- **Database Integration**: Easy integration with SQLite for accessing our existing database
- **Interactive Widgets**: Rich set of UI components for filtering, searching, and reviewing
- **Web-based**: Cross-platform compatibility without needing to install native desktop frameworks

### Advantages over alternatives:
- **vs PyQt**: Less complex setup, faster development, better for data applications
- **vs Tkinter**: More modern UI, better image handling, easier to style
- **vs Gradio**: More flexible for complex applications, better database integration
- **vs Pure HTML**: Better integration with Python backend, easier to add interactive features

## Proposed Architecture

### Streamlit App Structure
```
naval-gallery/
├── apps/
│   └── gallery_gui.py          # Main Streamlit application
├── src/
│   ├── vision/
│   │   └── client.py           # Existing vision client
│   ├── db.py                   # Database interface
│   └── gui/
│       ├── components/         # Reusable UI components
│       │   ├── image_viewer.py
│       │   ├── classification_panel.py
│       │   └── metadata_editor.py
│       └── pages/              # Multi-page app structure
│           ├── dashboard.py    # Overview page
│           ├── gallery.py      # Image browsing
│           ├── classification.py # AI analysis review
│           └── curation.py     # Curation workflow
```

### Key Features
1. **Dashboard**: Overview of collection statistics, analysis progress, and recent additions
2. **Gallery View**: Enhanced image grid with advanced filtering and search capabilities
3. **Classification Review**: Interface to review and correct AI vision classifications
4. **Curation Workflow**: Tools for moving images from staging to curated status
5. **Analysis Tools**: Detailed view of AI analysis results with confidence scores

## Implementation Plan

### Phase 1: Basic Streamlit App
- [ ] Set up basic Streamlit application structure
- [ ] Integrate with existing SQLite database
- [ ] Create basic image gallery view with filtering
- [ ] Display existing metadata (navy, type, era, etc.)

### Phase 2: AI Integration
- [ ] Display AI classification results alongside images
- [ ] Add confidence indicators and reasoning display
- [ ] Create interface for reviewing and correcting classifications
- [ ] Add batch processing capabilities

### Phase 3: Advanced Features
- [ ] Multi-page application structure
- [ ] Advanced search and filtering
- [ ] Export capabilities for curated collections
- [ ] Statistics and analytics dashboard

## Technical Considerations

### Dependencies
```toml
[project]
dependencies = [
    "streamlit>=1.28.0",
    "pandas>=1.5.0",
    "pillow>=9.0.0",
    "sqlite3",  # Built-in
    "requests>=2.31.0",
    "internetarchive>=3.5.0",
]
```

### UI Components
- **Image Grid**: Responsive grid for displaying naval drawings
- **Metadata Panel**: Detailed information display for selected images
- **Classification Widget**: Interface for viewing and editing AI classifications
- **Filter Sidebar**: Advanced filtering options (navy, era, type, confidence, etc.)
- **Action Buttons**: Tools for curation workflow (approve, reject, reclassify)

### Data Flow
1. Streamlit app connects to existing SQLite database
2. Images are loaded with their AI analysis results
3. Users can review, correct, and approve classifications
4. Changes are saved back to the database
5. Updated data can be exported to JSON manifests for the web gallery

## User Workflow

### For Curators
1. Launch Streamlit app: `streamlit run apps/gallery_gui.py`
2. Browse images in gallery view
3. Review AI classifications in dedicated interface
4. Correct classifications as needed
5. Approve images for inclusion in curated collection
6. Monitor statistics and progress

### For Researchers
1. Use enhanced filtering to find specific ship types or eras
2. Access detailed technical information extracted by AI
3. Export search results for research purposes

## Risks and Mitigation

### Risks
- **Performance**: Large image collections may impact UI responsiveness
- **Complexity**: Adding GUI layer may complicate the existing simple workflow
- **Maintenance**: Additional codebase to maintain

### Mitigation
- Implement lazy loading and caching for images
- Keep GUI focused on curation workflow, maintain existing HTML gallery for public viewing
- Use modular architecture to isolate GUI-specific code

## Success Metrics

- Improved curation efficiency (time to review and classify images)
- Better accuracy in classifications after human review
- Increased curator satisfaction with the workflow
- Successful integration with existing data pipeline

## Consequences

### Positive
- Enhanced curation workflow with visual interface
- Better visibility into AI analysis results
- Improved ability to quality-check automated classifications
- More accessible tool for non-technical curators

### Neutral
- Additional dependency on Streamlit
- Need to maintain both GUI and HTML interfaces
- Learning curve for curators to adopt new interface

### Negative
- Additional complexity in the codebase
- Potential performance considerations with large image sets
- Need for additional documentation and training

## Alternatives Considered

### PyQt Application
- More complex to develop and maintain
- Better for native desktop experience but overkill for current needs

### Enhanced HTML/JS Interface
- Would require significant JavaScript development
- Harder to integrate with Python AI components
- More complex state management

### Gradio Interface
- Good for quick prototyping but less flexible for complex applications
- Less suitable for long-term curation workflow

## Decision Drivers

- Need for better integration between AI analysis and human curation
- Desire for visual interface to improve curation workflow
- Requirement to display complex AI analysis results
- Need for advanced filtering and search capabilities
- Cross-platform compatibility requirements

## Implementation Timeline

- **Week 1-2**: Basic Streamlit app with database integration
- **Week 3-4**: Image gallery and filtering features
- **Week 5-6**: AI classification review interface
- **Week 7-8**: Advanced features and testing