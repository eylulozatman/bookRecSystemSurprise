document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const userSubmitBtn = document.getElementById('user-submit');
    const itemSubmitBtn = document.getElementById('item-submit');
    const errorAlert = document.getElementById('error-alert');
    
    // Autocomplete setup
    setupAutocomplete('user-id', '/api/search/users/');
    setupAutocomplete('book-isbn', '/api/search/books/');
    
    // Event listeners
    userSubmitBtn.addEventListener('click', getUserRecommendations);
    itemSubmitBtn.addEventListener('click', getItemRecommendations);
    
    function setupAutocomplete(inputId, endpoint) {
        const input = document.getElementById(inputId);
        const datalist = document.createElement('datalist');
        datalist.id = `${inputId}-list`;
        input.after(datalist);
        input.setAttribute('list', datalist.id);
        
        input.addEventListener('input', debounce(function() {
            if (this.value.length < 2) return;
            
            fetch(`${endpoint}${this.value}`)
                .then(handleResponse)
                .then(data => {
                    datalist.innerHTML = '';
                    data.results.forEach(item => {
                        const option = document.createElement('option');
                        option.value = inputId === 'user-id' ? item.user_id : item.isbn;
                        datalist.appendChild(option);
                    });
                })
                .catch(handleError);
        }, 300));
    }
    
    function getUserRecommendations() {
        const userId = document.getElementById('user-id').value.trim();
        const k = document.getElementById('user-k').value || 5;
        
        if (!userId) {
            showError('Please enter a valid user ID');
            return;
        }

        clearResults();
        
        fetch('/api/user-based/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ 
                user_id: userId, 
                k: parseInt(k) 
            })
        })
        .then(handleResponse)
        .then(data => {
            if (data.success) {
                if (data.recommendations.length === 0) {
                    showError('No recommendations found for this user');
                } else {
                    showUserResults(data);
                }
            } else {
                showError(data.error || 'Error getting recommendations');
            }
        })
        .catch(handleError);
    }

    function getItemRecommendations() {
        const isbn = document.getElementById('book-isbn').value.trim();
        const k = document.getElementById('item-k').value || 5;
        
        if (!isbn) {
            showError('Please enter a valid ISBN number');
            return;
        }

        clearResults();
        
        fetch('/api/item-based/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ 
                isbn: isbn, 
                k: parseInt(k) 
            })
        })
        .then(handleResponse)
        .then(data => {
            if (data.success) {
                if (data.recommendations.length === 0) {
                    showError('No similar books found for this ISBN');
                } else {
                    showItemResults(data);
                }
            } else {
                showError(data.error || 'Error finding similar books');
            }
        })
        .catch(handleError);
    }

    function showUserResults(data) {
        hideError();
        
        // Show similar users
        const similarUsersHTML = data.similar_users.map(user => `
            <span class="similar-user">
                ${user.user_id} 
                <span class="similarity">(similarity: ${user.similarity})</span>
            </span>
        `).join(' ');
        
        document.getElementById('similar-users').innerHTML = similarUsersHTML;
        
        // Show recommendations
        const recommendationsHTML = data.recommendations.map(book => `
            <tr>
                <td><img src="${book.image_url || 'https://via.placeholder.com/60x90?text=No+Cover'}" class="img-thumbnail"></td>
                <td>${book.title}<br><small class="text-muted">${book.isbn}</small></td>
                <td>${book.author}</td>
                <td>${book.predicted_score}</td>
                <td>${book.similarity}</td>
            </tr>
        `).join('');
        
        document.getElementById('user-recommendations').innerHTML = recommendationsHTML;
        document.getElementById('user-results').classList.remove('d-none');
        document.getElementById('item-results').classList.add('d-none');
    }

    function showItemResults(data) {
        hideError();
        
        // Show source book
        const sourceBookHTML = `
            <img src="${data.source_book.image_url || 'https://via.placeholder.com/60x90?text=No+Cover'}" class="img-thumbnail">
            <div class="source-book-info">
                <div class="source-book-title">${data.source_book.title}</div>
                <div class="source-book-author">${data.source_book.author}</div>
                <div class="text-muted small">ISBN: ${data.source_book.isbn}</div>
            </div>
        `;
        
        document.getElementById('source-book').innerHTML = sourceBookHTML;
        
        // Show similar books
        const recommendationsHTML = data.recommendations.map(book => `
            <tr>
                <td><img src="${book.image_url || 'https://via.placeholder.com/60x90?text=No+Cover'}" class="img-thumbnail"></td>
                <td>${book.title}<br><small class="text-muted">${book.isbn}</small></td>
                <td>${book.author}</td>
                <td>${book.similarity}</td>
                <td>${book.avg_rating}</td>
            </tr>
        `).join('');
        
        document.getElementById('item-recommendations').innerHTML = recommendationsHTML;
        document.getElementById('item-results').classList.remove('d-none');
        document.getElementById('user-results').classList.add('d-none');
    }

    function clearResults() {
        document.getElementById('user-recommendations').innerHTML = '';
        document.getElementById('item-recommendations').innerHTML = '';
        document.getElementById('similar-users').innerHTML = '';
        document.getElementById('source-book').innerHTML = '';
        document.getElementById('user-results').classList.add('d-none');
        document.getElementById('item-results').classList.add('d-none');
        hideError();
    }

    function handleResponse(response) {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Request failed');
            });
        }
        return response.json();
    }
    
    function handleError(error) {
        console.error('Error:', error);
        showError(error.message || 'An error occurred');
    }
    
    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.classList.remove('d-none');
    }
    
    function hideError() {
        errorAlert.classList.add('d-none');
    }
    
    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this, args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }
});