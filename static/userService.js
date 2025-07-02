// Navigation buttons
document.getElementById('backBtn').addEventListener('click', () => {
  window.location.href = '/';
});

document.getElementById('myBookListBtn').addEventListener('click', async () => {
  const userId = document.getElementById('userIdDisplay').textContent;

  try {
    const res = await fetch(`/api/user/${userId}/has-rated`);
    const data = await res.json();

    if (data.success && data.count < 5) {
      showRatingPopup(userId, data.count);
    } else {
      window.location.href = `/mybooklist/${userId}`;
    }
  } catch (error) {
    console.error('Error checking user rating status:', error);
  }
});

let currentPage = 1;
let totalPages = 1;
let currentQuery = '';
let userAddedISBNs = [];
const userId = document.getElementById('userIdDisplay').textContent;

// Load user's added books on page load
loadUserBooks();

async function loadUserBooks() {
  try {
    const response = await fetch(`/api/user/${userId}/added-isbns`);
    const data = await response.json();
    if (data.success) {
      userAddedISBNs = data.isbns || [];
    }
  } catch (error) {
    console.error('Error loading user books:', error);
  }
}

document.getElementById('searchBtn').addEventListener('click', () => {
  currentPage = 1;
  const query = document.getElementById('searchInput').value.trim();
  if (query) {
    currentQuery = query;
    performSearch(query, currentPage);
  } else {
    alert('Please enter a search term');
  }
});

async function performSearch(query, page) {
  try {
    const res = await fetch(`/api/search/books/${encodeURIComponent(query)}?page=${page}`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

    const data = await res.json();
    const resultsDiv = document.getElementById('searchResults');
    resultsDiv.innerHTML = '';

    if (!data.success) {
      resultsDiv.textContent = data.message || 'Search failed';
      document.getElementById('pagination').innerHTML = '';
      return;
    }

    if (!data.results || data.results.length === 0) {
      resultsDiv.textContent = 'No books found.';
      document.getElementById('pagination').innerHTML = '';
      return;
    }

    totalPages = Math.ceil(data.total / 5);

    data.results.forEach(book => {
      const item = document.createElement('div');
      item.classList.add('result-item');

      const img = document.createElement('img');
      img.src = book["Image-URL-M"] || 'https://via.placeholder.com/70x100?text=No+Cover';
      img.alt = "Book Cover";
      item.appendChild(img);

      const bookInfo = document.createElement('div');
      bookInfo.classList.add('book-info');

      const title = document.createElement('div');
      title.innerHTML = `<strong>${book["Book-Title"]}</strong>`;
      bookInfo.appendChild(title);

      const author = document.createElement('div');
      author.textContent = `by ${book["Book-Author"]}`;
      bookInfo.appendChild(author);

      const isbn = document.createElement('div');
      isbn.textContent = `ISBN: ${book["ISBN"]}`;
      bookInfo.appendChild(isbn);

      const ratingSection = document.createElement('div');
      ratingSection.classList.add('rating-section');

      const select = document.createElement('select');
      select.classList.add('rating-dropdown');

      const emptyOption = document.createElement('option');
      emptyOption.value = '';
      emptyOption.textContent = 'Rate';
      select.appendChild(emptyOption);

      for (let i = 1; i <= 10; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = i;
        select.appendChild(option);
      }

      const addBtn = document.createElement('button');
      addBtn.textContent = 'Add Book';

      if (userAddedISBNs.includes(book.ISBN)) {
        addBtn.style.display = 'none';
        select.style.display = 'none';
        markAsAdded(ratingSection);
      }

      addBtn.addEventListener('click', async () => {
        const selectedRating = select.value;
        if (!selectedRating) {
          alert("Please select a rating first!");
          return;
        }

        await addBookForUser(userId, book, selectedRating, () => {
          alert(`Book added successfully!`);
          addBtn.style.display = 'none';
          select.style.display = 'none';
          markAsAdded(ratingSection);
        });
      });

      ratingSection.appendChild(select);
      ratingSection.appendChild(addBtn);
      bookInfo.appendChild(ratingSection);
      item.appendChild(bookInfo);
      resultsDiv.appendChild(item);
    });

    updatePaginationControls();
  } catch (error) {
    console.error('Search error:', error);
    document.getElementById('searchResults').textContent = 'Error during search: ' + error.message;
  }
}

function markAsAdded(ratingSection) {
  const addedLabel = document.createElement('span');
  addedLabel.textContent = '✓ Already in your library';
  addedLabel.style.color = 'red';
  addedLabel.style.fontWeight = 'bold';
  ratingSection.appendChild(addedLabel);
}

function updatePaginationControls() {
  const paginationDiv = document.getElementById('pagination');
  paginationDiv.innerHTML = '';

  if (totalPages <= 1) return;

  const prevButton = document.createElement('button');
  prevButton.textContent = 'Previous';
  prevButton.disabled = currentPage === 1;
  prevButton.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      performSearch(currentQuery, currentPage);
    }
  });

  const nextButton = document.createElement('button');
  nextButton.textContent = 'Next';
  nextButton.disabled = currentPage >= totalPages;
  nextButton.addEventListener('click', () => {
    if (currentPage < totalPages) {
      currentPage++;
      performSearch(currentQuery, currentPage);
    }
  });

  const pageInfo = document.createElement('span');
  pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  pageInfo.style.margin = '0 10px';

  paginationDiv.appendChild(prevButton);
  paginationDiv.appendChild(pageInfo);
  paginationDiv.appendChild(nextButton);
}

// Modular addBook function
async function addBookForUser(userId, book, rating, onSuccess) {
  try {
    const response = await fetch(`/api/user/${userId}/add-book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        isbn: book.ISBN,
        rating,
        title: book["Book-Title"],
        author: book["Book-Author"],
        image: book["Image-URL-M"]
      })
    });

    const result = await response.json();
    if (result.success) {
      userAddedISBNs.push(book.ISBN);
      if (typeof onSuccess === 'function') onSuccess();
    } else {
      alert(`Failed to add book: ${result.message || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error adding book:', error);
    alert('An error occurred while adding the book.');
  }
}

// Popup for rating if less than 5 rated books
async function showRatingPopup(userId, initialCount) {
  let ratingCount = initialCount;
  let popupRatedBooks = [...userAddedISBNs];

  const popup = document.createElement('div');
  popup.id = 'ratingPopup';
  popup.className = 'popup-overlay';
  popup.innerHTML = `
    <div class="popup-content">
      <h3>Please rate at least 5 books to continue</h3>
      <div id="popupBookList" class="popup-list"></div>
      <button id="skipBooksBtn">Skip and Load New Books</button>
    </div>
  `;
  document.body.appendChild(popup);

  document.getElementById('skipBooksBtn').addEventListener('click', loadRandomBooks);
  await loadRandomBooks();

  async function loadRandomBooks() {
    const query = `/api/random-books?` + popupRatedBooks.map(isbn => `exclude=${isbn}`).join('&');
    const res = await fetch(query);
    const data = await res.json();

    const bookListDiv = document.getElementById('popupBookList');
    bookListDiv.innerHTML = '';

    if (!data.success || !data.books || data.books.length === 0) {
      bookListDiv.innerHTML = '<p>No books available.</p>';
      return;
    }

    data.books.forEach(book => {
      const wrapper = document.createElement('div');
      wrapper.classList.add('popup-book');

      wrapper.innerHTML = `
        <img src="${book["Image-URL-M"] || 'https://via.placeholder.com/60x90'}" width="60" height="90" />
        <div class="popup-book-info">
          <strong>${book["Book-Title"]}</strong> by ${book["Book-Author"]}<br />
          ISBN: ${book.ISBN}
          <select class="popup-rating">
            <option value="">Rate</option>
            ${[...Array(10).keys()].map(i => `<option value="${i + 1}">${i + 1}</option>`).join('')}
          </select>
          <div class="rating-status" style="margin-top: 5px;"></div>
        </div>
      `;

      const ratingDropdown = wrapper.querySelector('.popup-rating');
      const statusDiv = wrapper.querySelector('.rating-status');

      ratingDropdown.addEventListener('change', async () => {
        const selectedRating = ratingDropdown.value;
        if (!selectedRating) return;

        await addBookForUser(userId, book, selectedRating, () => {
          ratingCount++;
          popupRatedBooks.push(book.ISBN);

          // Değiştirilen içerik burada
          ratingDropdown.disabled = true;
          statusDiv.textContent = `✅ Added to list. Score: ${selectedRating}`;
          statusDiv.style.color = '#e53935';

          if (ratingCount >= 5) {
            setTimeout(() => {
              popup.remove();
              window.location.href = `/mybooklist/${userId}`;
            }, 1000);
          }
        });
      });

      bookListDiv.appendChild(wrapper);
    });
  }
}
