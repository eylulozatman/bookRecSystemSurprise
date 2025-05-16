document.addEventListener('DOMContentLoaded', function() {
    const userSubmitBtn = document.getElementById('user-submit-btn');
    const itemSubmitBtn = document.getElementById('item-submit-btn');
    const errorAlert = document.getElementById('error-message');

    // Otomatik tamamlama fonksiyonları
    setupAutocomplete('user-id-input', '/api/autofill/users/');
    setupAutocomplete('book-isbn-input', '/api/autofill/books/');

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
                if (data.results && Array.isArray(data.results)) {
                    data.results.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.user_id || item.isbn;
                        option.textContent = item.user_id || item.isbn;
                        datalist.appendChild(option);
                    });
                }
            })
            .catch(handleError);
    }, 300));
}
    function getUserRecommendations() {
        const userId = document.getElementById('user-id-input').value.trim();
        const k = document.getElementById('user-k-input').value || 5;

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
                if (!data.recommendations || data.recommendations.length === 0) {
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
    const isbn = document.getElementById('book-isbn-input').value.trim();
    const k = document.getElementById('item-k-input').value || 5;
    
    console.log("Sending item-based request with:", {isbn, k});

    if (!isbn) {
        showError('Please enter a valid ISBN number');
        return;
    }

    fetch('/api/item-based/recommend', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({ isbn, k: parseInt(k) })
    })
    .then(response => {
        console.log("Raw response:", response);
        if (!response.ok) {
            return response.json().then(err => {
                console.error("API Error:", err);
                throw new Error(err.error || 'Request failed');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed data:", data);
        if (data.success) {
            if (!data.recommendations || data.recommendations.length === 0) {
                showError('No similar books found for this ISBN');
            } else {
                showItemResults(data);
            }
        } else {
            showError(data.error || 'Error finding similar books');
        }
    })
    .catch(error => {
        console.error("Full error:", error);
        showError(error.message || 'Failed to get recommendations');
    });
}

    function showUserResults(data) {
        hideError();

        // Benzer kullanıcıları göster
        const similarUsersHTML = (data.similar_users || []).map(user => `
            <span class="similar-user">
                ${user.user_id}
                <span class="similarity">(similarity: ${user.similarity})</span>
            </span>
        `).join(' ');

        document.getElementById('similar-users').innerHTML = similarUsersHTML;

        // Kullanıcıya önerilen kitaplar
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

        // Kaynak kitabı göster
        const sourceBook = data.source_book || {};
        const sourceBookHTML = `
            <img src="${sourceBook.image_url || 'https://via.placeholder.com/60x90?text=No+Cover'}" class="img-thumbnail">
            <div class="source-book-info">
                <div class="source-book-title">${sourceBook.title || 'Unknown Title'}</div>
                <div class="source-book-author">${sourceBook.author || 'Unknown Author'}</div>
                <div class="text-muted small">ISBN: ${sourceBook.isbn || 'N/A'}</div>
            </div>
        `;

        document.getElementById('source-book').innerHTML = sourceBookHTML;

        // Benzer kitapları göster
        const recommendationsHTML = (data.recommendations || []).map(book => `
            <tr>
                <td><img src="${book.image_url || 'https://via.placeholder.com/60x90?text=No+Cover'}" class="img-thumbnail"></td>
                <td>${book.title}<br><small class="text-muted">${book.isbn}</small></td>
                <td>${book.author}</td>
                <td>${book.similarity}</td>
                <td>${book.avg_rating || '-'}</td>
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
