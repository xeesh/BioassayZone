// Bioassay Zone Measurement Tool - Main JavaScript

class BioassayTool {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.image = null;
        this.zones = [];
        this.selectedZone = null;
        this.isManualMode = false;
        this.isDrawing = false;
        this.startPoint = null;
        this.zoomLevel = 1.0;
        this.panOffset = { x: 0, y: 0 };
        this.isPanning = false;
        this.lastPanPoint = null;
        
        this.init();
    }
    
    init() {
        // Initialize event listeners
        this.setupEventListeners();
        
        // Check if we're on the analysis page
        if (document.getElementById('imageCanvas')) {
            this.initializeCanvas();
        }
    }
    
    setupEventListeners() {
        // Upload form
        const uploadForm = document.getElementById('uploadForm');
        if (uploadForm) {
            uploadForm.addEventListener('submit', this.handleUpload.bind(this));
        }
        
        // Analysis page controls
        const detectBtn = document.getElementById('detectZonesBtn');
        if (detectBtn) {
            detectBtn.addEventListener('click', this.detectZones.bind(this));
        }
        
        const manualBtn = document.getElementById('manualModeBtn');
        if (manualBtn) {
            manualBtn.addEventListener('click', this.toggleManualMode.bind(this));
        }
        
        const clearBtn = document.getElementById('clearZonesBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', this.clearZones.bind(this));
        }
        
        const calcStatsBtn = document.getElementById('calculateStatsBtn');
        if (calcStatsBtn) {
            calcStatsBtn.addEventListener('click', this.calculateStatistics.bind(this));
        }
        
        const reportBtn = document.getElementById('generateReportBtn');
        if (reportBtn) {
            reportBtn.addEventListener('click', this.generateReport.bind(this));
        }
        
        const auditBtn = document.getElementById('viewAuditBtn');
        if (auditBtn) {
            auditBtn.addEventListener('click', this.viewAuditLog.bind(this));
        }
        
        // Zoom control
        const zoomSlider = document.getElementById('zoomLevel');
        if (zoomSlider) {
            zoomSlider.addEventListener('input', this.handleZoom.bind(this));
        }
        
        // Grid toggle
        const gridToggle = document.getElementById('showGrid');
        if (gridToggle) {
            gridToggle.addEventListener('change', this.toggleGrid.bind(this));
        }
    }
    
    initializeCanvas() {
        this.canvas = document.getElementById('imageCanvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Setup canvas event listeners
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('contextmenu', this.handleRightClick.bind(this));
        this.canvas.addEventListener('wheel', this.handleWheel.bind(this));
        
        // Load the image
        this.loadImage();
    }
    
    async loadImage() {
        const assayData = document.getElementById('assayData');
        const assayId = assayData.dataset.assayId;
        
        try {
            this.showLoading(true);
            
            const img = new Image();
            img.onload = () => {
                this.image = img;
                this.resizeCanvas();
                this.drawCanvas();
                this.showLoading(false);
            };
            
            img.onerror = () => {
                this.showError('Failed to load image');
                this.showLoading(false);
            };
            
            img.src = `/get_image/${assayId}`;
            
        } catch (error) {
            this.showError(`Image loading failed: ${error.message}`);
            this.showLoading(false);
        }
    }
    
    resizeCanvas() {
        if (!this.image) return;
        
        const container = this.canvas.parentElement;
        const maxWidth = container.clientWidth - 20;
        const maxHeight = 500;
        
        const aspectRatio = this.image.width / this.image.height;
        let canvasWidth = Math.min(maxWidth, this.image.width);
        let canvasHeight = canvasWidth / aspectRatio;
        
        if (canvasHeight > maxHeight) {
            canvasHeight = maxHeight;
            canvasWidth = canvasHeight * aspectRatio;
        }
        
        this.canvas.width = canvasWidth;
        this.canvas.height = canvasHeight;
        
        // Store original dimensions for calculations
        this.originalWidth = canvasWidth;
        this.originalHeight = canvasHeight;
    }
    
    drawCanvas() {
        if (!this.image || !this.ctx) return;
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Apply zoom and pan
        this.ctx.save();
        this.ctx.scale(this.zoomLevel, this.zoomLevel);
        this.ctx.translate(this.panOffset.x, this.panOffset.y);
        
        // Draw image
        this.ctx.drawImage(this.image, 0, 0, this.canvas.width / this.zoomLevel, this.canvas.height / this.zoomLevel);
        
        // Draw zones
        this.drawZones();
        
        this.ctx.restore();
    }
    
    drawZones() {
        if (!this.zones || this.zones.length === 0) return;
        
        this.zones.forEach((zone, index) => {
            const isSelected = this.selectedZone === zone;
            
            // Set style based on zone type
            if (zone.type === 'automatic') {
                this.ctx.strokeStyle = isSelected ? '#007bff' : '#28a745';
            } else {
                this.ctx.strokeStyle = isSelected ? '#007bff' : '#ffc107';
            }
            
            this.ctx.lineWidth = isSelected ? 3 : 2;
            this.ctx.setLineDash([]);
            
            // Draw circle
            this.ctx.beginPath();
            this.ctx.arc(zone.x, zone.y, zone.radius, 0, 2 * Math.PI);
            this.ctx.stroke();
            
            // Draw label
            this.ctx.fillStyle = '#000';
            this.ctx.font = '12px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(`${index + 1}`, zone.x, zone.y - zone.radius - 5);
            this.ctx.fillText(`${zone.diameter_mm}mm`, zone.x, zone.y + zone.radius + 15);
        });
    }
    
    handleMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / this.zoomLevel - this.panOffset.x;
        const y = (e.clientY - rect.top) / this.zoomLevel - this.panOffset.y;
        
        if (this.isManualMode) {
            // Start drawing a zone
            this.isDrawing = true;
            this.startPoint = { x, y };
        } else {
            // Check for zone selection or start panning
            const clickedZone = this.findZoneAt(x, y);
            if (clickedZone) {
                this.selectZone(clickedZone);
            } else {
                // Start panning
                this.isPanning = true;
                this.lastPanPoint = { x: e.clientX, y: e.clientY };
                this.canvas.style.cursor = 'grabbing';
            }
        }
    }
    
    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / this.zoomLevel - this.panOffset.x;
        const y = (e.clientY - rect.top) / this.zoomLevel - this.panOffset.y;
        
        if (this.isDrawing && this.startPoint) {
            // Preview the zone being drawn
            this.drawCanvas();
            
            const radius = Math.sqrt(Math.pow(x - this.startPoint.x, 2) + Math.pow(y - this.startPoint.y, 2));
            
            this.ctx.save();
            this.ctx.scale(this.zoomLevel, this.zoomLevel);
            this.ctx.translate(this.panOffset.x, this.panOffset.y);
            
            this.ctx.strokeStyle = '#ffc107';
            this.ctx.lineWidth = 2;
            this.ctx.setLineDash([5, 5]);
            this.ctx.beginPath();
            this.ctx.arc(this.startPoint.x, this.startPoint.y, radius, 0, 2 * Math.PI);
            this.ctx.stroke();
            
            this.ctx.restore();
        } else if (this.isPanning && this.lastPanPoint) {
            // Handle panning
            const deltaX = (e.clientX - this.lastPanPoint.x) / this.zoomLevel;
            const deltaY = (e.clientY - this.lastPanPoint.y) / this.zoomLevel;
            
            this.panOffset.x += deltaX;
            this.panOffset.y += deltaY;
            
            this.lastPanPoint = { x: e.clientX, y: e.clientY };
            this.drawCanvas();
        }
    }
    
    handleMouseUp(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / this.zoomLevel - this.panOffset.x;
        const y = (e.clientY - rect.top) / this.zoomLevel - this.panOffset.y;
        
        if (this.isDrawing && this.startPoint) {
            // Create manual zone
            const radius = Math.sqrt(Math.pow(x - this.startPoint.x, 2) + Math.pow(y - this.startPoint.y, 2));
            
            if (radius > 5) { // Minimum radius
                this.addManualZone(this.startPoint.x, this.startPoint.y, radius);
            }
            
            this.isDrawing = false;
            this.startPoint = null;
        }
        
        if (this.isPanning) {
            this.isPanning = false;
            this.lastPanPoint = null;
            this.canvas.style.cursor = this.isManualMode ? 'crosshair' : 'default';
        }
    }
    
    handleRightClick(e) {
        e.preventDefault();
        
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / this.zoomLevel - this.panOffset.x;
        const y = (e.clientY - rect.top) / this.zoomLevel - this.panOffset.y;
        
        const clickedZone = this.findZoneAt(x, y);
        if (clickedZone) {
            this.showZoneDetails(clickedZone);
        }
    }
    
    handleWheel(e) {
        e.preventDefault();
        
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newZoom = Math.max(0.5, Math.min(3.0, this.zoomLevel + delta));
        
        if (newZoom !== this.zoomLevel) {
            this.zoomLevel = newZoom;
            document.getElementById('zoomLevel').value = newZoom * 100;
            document.getElementById('zoomValue').textContent = Math.round(newZoom * 100) + '%';
            this.drawCanvas();
        }
    }
    
    findZoneAt(x, y) {
        return this.zones.find(zone => {
            const distance = Math.sqrt(Math.pow(x - zone.x, 2) + Math.pow(y - zone.y, 2));
            return distance <= zone.radius;
        });
    }
    
    selectZone(zone) {
        this.selectedZone = zone;
        this.drawCanvas();
        this.updateZonesList();
    }
    
    toggleManualMode() {
        this.isManualMode = !this.isManualMode;
        const btn = document.getElementById('manualModeBtn');
        const toolsCard = document.getElementById('manualToolsCard');
        
        if (this.isManualMode) {
            btn.classList.add('active');
            toolsCard.classList.remove('d-none');
            this.canvas.style.cursor = 'crosshair';
            btn.innerHTML = '<i class="fas fa-check me-1"></i>Manual Mode';
        } else {
            btn.classList.remove('active');
            toolsCard.classList.add('d-none');
            this.canvas.style.cursor = 'default';
            btn.innerHTML = '<i class="fas fa-edit me-1"></i>Manual Mode';
        }
    }
    
    async handleUpload(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const uploadBtn = document.getElementById('uploadBtn');
        const progressBar = document.getElementById('uploadProgress');
        
        try {
            // Show loading state
            uploadBtn.classList.add('loading');
            uploadBtn.disabled = true;
            progressBar.classList.remove('d-none');
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Redirect to analysis page
                window.location.href = '/analysis';
            } else {
                this.showError(result.error || 'Upload failed');
            }
            
        } catch (error) {
            this.showError(`Upload failed: ${error.message}`);
        } finally {
            uploadBtn.classList.remove('loading');
            uploadBtn.disabled = false;
            progressBar.classList.add('d-none');
        }
    }
    
    async detectZones() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/detect_zones', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.zones = result.zones;
                this.updateZonesList();
                this.drawCanvas();
                this.showSuccess(`Detected ${result.zones.length} zones`);
                
                // Enable statistics calculation
                if (this.zones.length > 0) {
                    document.getElementById('calculateStatsBtn').classList.remove('d-none');
                    document.getElementById('generateReportBtn').disabled = false;
                }
            } else {
                this.showError(result.error || 'Detection failed');
            }
            
        } catch (error) {
            this.showError(`Detection failed: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }
    
    async addManualZone(x, y, radius) {
        const diameterInput = document.getElementById('manualDiameter');
        const diameter = parseFloat(diameterInput.value) || 15;
        
        // Convert diameter to radius (adjust for display)
        const adjustedRadius = (diameter / 25.4) * 300 / 2; // Approximate conversion
        
        try {
            const response = await fetch('/add_manual_zone', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    x: x,
                    y: y,
                    radius: adjustedRadius,
                    diameter_mm: diameter
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.zones.push(result.zone);
                this.updateZonesList();
                this.drawCanvas();
                
                // Enable controls
                document.getElementById('calculateStatsBtn').classList.remove('d-none');
                document.getElementById('generateReportBtn').disabled = false;
            } else {
                this.showError(result.error || 'Failed to add zone');
            }
            
        } catch (error) {
            this.showError(`Failed to add zone: ${error.message}`);
        }
    }
    
    clearZones() {
        if (confirm('Are you sure you want to clear all zones?')) {
            this.zones = [];
            this.selectedZone = null;
            this.updateZonesList();
            this.drawCanvas();
            
            // Disable controls
            document.getElementById('calculateStatsBtn').classList.add('d-none');
            document.getElementById('generateReportBtn').disabled = true;
            this.clearStatistics();
        }
    }
    
    async calculateStatistics() {
        if (this.zones.length === 0) {
            this.showError('No zones to analyze');
            return;
        }
        
        try {
            const response = await fetch('/calculate_statistics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    zones: this.zones
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.displayStatistics(result.statistics);
                this.showSuccess('Statistics calculated successfully');
            } else {
                this.showError(result.error || 'Statistics calculation failed');
            }
            
        } catch (error) {
            this.showError(`Statistics calculation failed: ${error.message}`);
        }
    }
    
    async generateReport() {
        if (this.zones.length === 0) {
            this.showError('No zones to include in report');
            return;
        }
        
        try {
            const reportBtn = document.getElementById('generateReportBtn');
            reportBtn.classList.add('loading');
            reportBtn.disabled = true;
            
            const response = await fetch('/generate_report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    zones: this.zones
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Open report in new tab
                window.open(result.report_url, '_blank');
                this.showSuccess('Report generated successfully');
            } else {
                this.showError(result.error || 'Report generation failed');
            }
            
        } catch (error) {
            this.showError(`Report generation failed: ${error.message}`);
        } finally {
            const reportBtn = document.getElementById('generateReportBtn');
            reportBtn.classList.remove('loading');
            reportBtn.disabled = false;
        }
    }
    
    async viewAuditLog() {
        try {
            const response = await fetch('/audit_log');
            const result = await response.json();
            
            if (result.success) {
                this.displayAuditLog(result.audit_entries);
            } else {
                this.showError(result.error || 'Failed to load audit log');
            }
            
        } catch (error) {
            this.showError(`Failed to load audit log: ${error.message}`);
        }
    }
    
    updateZonesList() {
        const container = document.getElementById('zonesList');
        
        if (this.zones.length === 0) {
            container.innerHTML = `
                <div class="text-muted text-center py-3">
                    <i class="fas fa-search fa-2x mb-2"></i>
                    <div>No zones detected yet</div>
                    <small>Click "Auto Detect" to analyze the image</small>
                </div>
            `;
            return;
        }
        
        const zonesHTML = this.zones.map((zone, index) => `
            <div class="zone-item ${this.selectedZone === zone ? 'selected' : ''}" data-zone-id="${zone.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>Zone ${index + 1}</strong>
                        <span class="badge zone-badge ${zone.type} ms-2">${zone.type}</span>
                        <div class="small text-muted mt-1">
                            Position: (${Math.round(zone.x)}, ${Math.round(zone.y)})<br>
                            Diameter: ${zone.diameter_mm} mm
                        </div>
                    </div>
                    <div class="text-end">
                        ${zone.confidence ? `<small class="text-muted">Confidence: ${Math.round(zone.confidence * 100)}%</small>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = zonesHTML;
        
        // Add click handlers
        container.querySelectorAll('.zone-item').forEach((item, index) => {
            item.addEventListener('click', () => {
                this.selectZone(this.zones[index]);
            });
        });
    }
    
    displayStatistics(stats) {
        const container = document.getElementById('statisticsContent');
        
        const statsHTML = `
            <table class="table table-sm stats-table">
                <tr>
                    <td>Count:</td>
                    <td class="stats-value">${stats.count}</td>
                </tr>
                <tr>
                    <td>Mean:</td>
                    <td class="stats-value">${stats.mean} mm</td>
                </tr>
                <tr>
                    <td>Median:</td>
                    <td class="stats-value">${stats.median} mm</td>
                </tr>
                <tr>
                    <td>Std Dev:</td>
                    <td class="stats-value">${stats.std_dev} mm</td>
                </tr>
                <tr>
                    <td>CV%:</td>
                    <td class="stats-value">${stats.cv_percent}%</td>
                </tr>
                <tr>
                    <td>Range:</td>
                    <td class="stats-value">${stats.min} - ${stats.max} mm</td>
                </tr>
            </table>
        `;
        
        container.innerHTML = statsHTML;
    }
    
    clearStatistics() {
        const container = document.getElementById('statisticsContent');
        container.innerHTML = `
            <div class="text-muted text-center py-3">
                <i class="fas fa-chart-bar fa-2x mb-2"></i>
                <div>No statistics available</div>
                <small>Analyze zones to see statistics</small>
            </div>
        `;
    }
    
    displayAuditLog(entries) {
        const container = document.getElementById('auditContent');
        const modal = new bootstrap.Modal(document.getElementById('auditModal'));
        
        if (entries.length === 0) {
            container.innerHTML = '<p class="text-muted">No audit entries found.</p>';
        } else {
            const entriesHTML = entries.map(entry => `
                <div class="audit-entry">
                    <div class="audit-timestamp">${new Date(entry.timestamp).toLocaleString()}</div>
                    <div class="audit-action">${entry.action}</div>
                    <div class="audit-description">${entry.description}</div>
                    <small class="text-muted">User: ${entry.user}</small>
                </div>
            `).join('');
            
            container.innerHTML = entriesHTML;
        }
        
        modal.show();
    }
    
    showZoneDetails(zone) {
        const zoneIndex = this.zones.indexOf(zone) + 1;
        const details = `
            <table class="table table-sm">
                <tr>
                    <td><strong>Zone ID:</strong></td>
                    <td>${zone.id}</td>
                </tr>
                <tr>
                    <td><strong>Type:</strong></td>
                    <td><span class="badge zone-badge ${zone.type}">${zone.type}</span></td>
                </tr>
                <tr>
                    <td><strong>Position:</strong></td>
                    <td>(${Math.round(zone.x)}, ${Math.round(zone.y)})</td>
                </tr>
                <tr>
                    <td><strong>Radius:</strong></td>
                    <td>${Math.round(zone.radius)} pixels</td>
                </tr>
                <tr>
                    <td><strong>Diameter:</strong></td>
                    <td>${zone.diameter_mm} mm</td>
                </tr>
                ${zone.confidence ? `
                <tr>
                    <td><strong>Confidence:</strong></td>
                    <td>${Math.round(zone.confidence * 100)}%</td>
                </tr>
                ` : ''}
            </table>
        `;
        
        document.getElementById('zoneDetails').innerHTML = details;
        
        const deleteBtn = document.getElementById('deleteZoneBtn');
        deleteBtn.onclick = () => this.deleteZone(zone);
        
        const modal = new bootstrap.Modal(document.getElementById('zoneModal'));
        modal.show();
    }
    
    deleteZone(zone) {
        const index = this.zones.indexOf(zone);
        if (index > -1) {
            this.zones.splice(index, 1);
            if (this.selectedZone === zone) {
                this.selectedZone = null;
            }
            this.updateZonesList();
            this.drawCanvas();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('zoneModal'));
            modal.hide();
            
            this.showSuccess('Zone deleted successfully');
        }
    }
    
    handleZoom(e) {
        this.zoomLevel = e.target.value / 100;
        document.getElementById('zoomValue').textContent = e.target.value + '%';
        this.drawCanvas();
    }
    
    toggleGrid(e) {
        // Grid functionality can be implemented here
        // For now, just acknowledge the toggle
        console.log('Grid toggle:', e.target.checked);
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            if (show) {
                overlay.classList.remove('d-none');
            } else {
                overlay.classList.add('d-none');
            }
        }
    }
    
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    showAlert(message, type) {
        const alertContainer = document.createElement('div');
        alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertContainer.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
        alertContainer.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertContainer);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertContainer.parentNode) {
                alertContainer.remove();
            }
        }, 5000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.bioassayTool = new BioassayTool();
});

// Analysis page initialization function
function initializeAnalysisPage() {
    console.log('Analysis page initialized');
}
