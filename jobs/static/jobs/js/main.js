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