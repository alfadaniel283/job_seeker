// Main JavaScript for AI Job Aggregator

$(document).ready(function() {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Add loading spinner for AJAX requests
    $(document).ajaxStart(function() {
        if ($('#spinner-overlay').length === 0) {
            $('body').append(`
                <div id="spinner-overlay" class="spinner-overlay">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `);
        }
    }).ajaxStop(function() {
        $('#spinner-overlay').remove();
    });
});

// Utility function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Utility function to truncate text
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Function to handle AJAX errors
function handleAjaxError(xhr, status, error) {
    console.error('AJAX Error:', error);
    let message = 'An error occurred. Please try again.';
    
    if (xhr.responseJSON && xhr.responseJSON.error) {
        message = xhr.responseJSON.error;
    } else if (xhr.status === 403) {
        message = 'You do not have permission to perform this action.';
    } else if (xhr.status === 404) {
        message = 'Resource not found.';
    } else if (xhr.status === 500) {
        message = 'Server error. Please try again later.';
    }
    
    showAlert('danger', message);
}

// Function to show alerts
function showAlert(type, message) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('.messages').append(alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
}

// Function to evaluate a single job
function evaluateJob(jobId) {
    $.ajax({
        url: '/jobs/api/evaluate-jobs/',
        method: 'POST',
        data: {
            job_ids: [jobId],
            use_ai: 'true',
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(data) {
            if (data.results && data.results.length > 0) {
                const result = data.results[0];
                showAlert('success', 
                    `✅ Job analyzed! Score: ${result.score}% - ${result.is_recommended ? 'Recommended' : 'Not Recommended'}`
                );
                // Reload the page to show updated evaluation
                setTimeout(function() {
                    location.reload();
                }, 1500);
            }
        },
        error: function(xhr, status, error) {
            handleAjaxError(xhr, status, error);
        }
    });
}

// Function to evaluate all jobs
function evaluateAllJobs() {
    const jobIds = [];
    $('.job-card').each(function() {
        jobIds.push($(this).data('job-id'));
    });
    
    if (jobIds.length === 0) {
        showAlert('warning', 'No jobs to evaluate');
        return;
    }
    
    if (!confirm(`Evaluate ${jobIds.length} jobs with AI? This may take a moment.`)) {
        return;
    }
    
    $.ajax({
        url: '/jobs/api/evaluate-jobs/',
        method: 'POST',
        data: {
            job_ids: jobIds,
            use_ai: 'true',
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(data) {
            showAlert('success', 
                `✅ Evaluated ${data.total_evaluated} jobs with AI!`
            );
            setTimeout(function() {
                location.reload();
            }, 1500);
        },
        error: function(xhr, status, error) {
            handleAjaxError(xhr, status, error);
        }
    });
}

// Function to get CSRF token
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
           '';
}

// Function to save preferences
function savePreferences() {
    const form = $('#preferences-form');
    if (!form.length) return;
    
    $.ajax({
        url: form.attr('action'),
        method: 'POST',
        data: form.serialize(),
        success: function(data) {
            showAlert('success', '✅ Preferences saved successfully!');
        },
        error: function(xhr, status, error) {
            handleAjaxError(xhr, status, error);
        }
    });
}

// Function to analyze job with AI
function analyzeWithAI(jobId) {
    $.ajax({
        url: `/jobs/api/ai-analyze/${jobId}/`,
        method: 'GET',
        success: function(data) {
            if (data.success) {
                showAlert('success', '✅ AI analysis complete!');
                setTimeout(function() {
                    location.reload();
                }, 1000);
            } else {
                showAlert('danger', '❌ Error: ' + data.error);
            }
        },
        error: function(xhr, status, error) {
            handleAjaxError(xhr, status, error);
        }
    });
}

// ============================================
// AI STRUCTURED DATA EXTRACTION FUNCTIONS
// ============================================

/**
 * Extract structured data from a job using AI
 */
function extractJobWithAI(jobId) {
    if (!confirm('Extract structured data from this job description using AI?')) {
        return;
    }
    
    // Find the extract button
    const btn = document.querySelector(`.extract-btn[data-job-id="${jobId}"]`) || 
                document.querySelector('.btn-primary .fa-robot')?.closest('button');
    
    if (btn) {
        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.dataset.originalHtml = originalHtml;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
    }
    
    $.ajax({
        url: `/jobs/api/extract-job-details/${jobId}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(data) {
            if (data.success) {
                showAlert('success', `✅ AI extraction complete! Updated fields: ${data.updated_fields.join(', ')}`);
                setTimeout(function() {
                    location.reload();
                }, 2000);
            } else {
                showAlert('danger', '❌ Error: ' + data.error);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = btn.dataset.originalHtml || '<i class="fas fa-robot"></i> Extract with AI';
                }
            }
        },
        error: function(xhr, status, error) {
            handleAjaxError(xhr, status, error);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = btn.dataset.originalHtml || '<i class="fas fa-robot"></i> Extract with AI';
            }
        }
    });
}

/**
 * Bulk extract structured data from all jobs
 */
function bulkExtractWithAI() {
    const jobCards = document.querySelectorAll('.job-card');
    const jobIds = [];
    jobCards.forEach(card => {
        jobIds.push(card.dataset.jobId);
    });
    
    if (jobIds.length === 0) {
        showAlert('warning', 'No jobs to extract');
        return;
    }
    
    if (!confirm(`Extract structured data from ${jobIds.length} jobs using AI? This may take a few minutes.`)) {
        return;
    }
    
    showAlert('info', '⏳ Starting bulk extraction...');
    
    // Add progress indicator
    const progressHtml = `
        <div id="extraction-progress" class="extraction-progress"></div>
        <div id="extraction-status" style="position:fixed;bottom:20px;right:20px;background:#333;color:white;padding:10px 20px;border-radius:8px;z-index:9998;display:none;">
            Processing: <span id="extraction-count">0</span>/<span id="extraction-total">${jobIds.length}</span>
        </div>
    `;
    $('body').append(progressHtml);
    $('#extraction-status').show();
    $('#extraction-total').text(jobIds.length);
    
    let processed = 0;
    let success = 0;
    
    jobIds.forEach(function(jobId, index) {
        setTimeout(function() {
            $.ajax({
                url: `/jobs/api/extract-job-details/${jobId}/`,
                method: 'POST',
                data: {
                    csrfmiddlewaretoken: getCsrfToken()
                },
                success: function(data) {
                    processed++;
                    if (data.success) success++;
                    updateExtractionProgress(processed, jobIds.length);
                    
                    if (processed === jobIds.length) {
                        $('#extraction-progress').remove();
                        $('#extraction-status').remove();
                        showAlert('success', `✅ Bulk extraction complete! ${success} of ${processed} jobs updated.`);
                        setTimeout(function() {
                            location.reload();
                        }, 2000);
                    }
                },
                error: function() {
                    processed++;
                    updateExtractionProgress(processed, jobIds.length);
                    
                    if (processed === jobIds.length) {
                        $('#extraction-progress').remove();
                        $('#extraction-status').remove();
                        showAlert('warning', `⚠️ Bulk extraction complete with errors. ${success} of ${processed} jobs updated.`);
                        setTimeout(function() {
                            location.reload();
                        }, 2000);
                    }
                }
            });
        }, index * 800); // 800ms delay between requests to avoid rate limiting
    });
}

/**
 * Update extraction progress indicator
 */
function updateExtractionProgress(processed, total) {
    const percentage = Math.round((processed / total) * 100);
    const progressEl = $('#extraction-progress');
    if (progressEl.length) {
        progressEl.css('width', percentage + '%');
    }
    
    // Update status text
    const countEl = $('#extraction-count');
    if (countEl.length) {
        countEl.text(processed);
    }
}

/**
 * Check if a job has AI extracted data
 */
function hasAIExtractedData(jobId) {
    const card = document.querySelector(`.job-card[data-job-id="${jobId}"]`);
    if (card) {
        return card.querySelector('.ai-enriched-badge') !== null;
    }
    return false;
}

/**
 * Display AI extraction summary on job detail page
 */
function showExtractionSummary(data) {
    if (!data) return;
    
    const summary = `
        <div class="alert alert-info mt-3">
            <h6><i class="fas fa-robot"></i> AI Extraction Summary</h6>
            <ul class="mb-0">
                <li>Requirements: ${data.requirements_count || 0}</li>
                <li>Responsibilities: ${data.responsibilities_count || 0}</li>
                <li>Benefits: ${data.benefits_count || 0}</li>
                <li>Skills: ${data.skills_count || 0}</li>
            </ul>
        </div>
    `;
    $('.job-detail-section:last').after(summary);
}

/**
 * Extract single job from detail page
 */
function extractDetailWithAI(jobId) {
    if (!confirm('Extract structured data from this job description using AI?')) {
        return;
    }
    
    const btn = document.querySelector('.btn-primary .fa-robot')?.closest('button');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
    }
    
    $.ajax({
        url: `/jobs/api/extract-job-details/${jobId}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: getCsrfToken()
        },
        success: function(data) {
            if (data.success) {
                showAlert('success', `✅ AI extraction complete! Updated fields: ${data.updated_fields.join(', ')}`);
                setTimeout(function() {
                    location.reload();
                }, 2000);
            } else {
                showAlert('danger', '❌ Error: ' + data.error);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-robot"></i> Extract with AI';
                }
            }
        },
        error: function(xhr, status, error) {
            handleAjaxError(xhr, status, error);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-robot"></i> Extract with AI';
            }
        }
    });
}

// Keyboard shortcuts
$(document).keydown(function(e) {
    // Ctrl+Enter to submit forms
    if (e.ctrlKey && e.key === 'Enter') {
        const form = $('form:visible').first();
        if (form.length) {
            form.submit();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        $('.modal').modal('hide');
    }
});

// Auto-refresh for job list (optional)
let refreshInterval = null;

function startAutoRefresh(interval = 60000) {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(function() {
        if ($('#job-list').length) {
            $.ajax({
                url: window.location.href,
                method: 'GET',
                success: function(data) {
                    const newContent = $(data).find('#job-list').html();
                    $('#job-list').html(newContent);
                }
            });
        }
    }, interval);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Export functions for use in templates
window.evaluateJob = evaluateJob;
window.evaluateAllJobs = evaluateAllJobs;
window.analyzeWithAI = analyzeWithAI;
window.showAlert = showAlert;
window.getCsrfToken = getCsrfToken;
window.truncateText = truncateText;
window.formatDate = formatDate;
window.extractJobWithAI = extractJobWithAI;
window.bulkExtractWithAI = bulkExtractWithAI;
window.extractDetailWithAI = extractDetailWithAI;
window.updateExtractionProgress = updateExtractionProgress;
window.hasAIExtractedData = hasAIExtractedData;
window.showExtractionSummary = showExtractionSummary;