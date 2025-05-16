// Navigation buttons
document.getElementById('backBtn').addEventListener('click', () => {
  window.location.href = '/';
});

document.getElementById('myBookListBtn').addEventListener('click', () => {
  const userId = document.getElementById('userIdDisplay').textContent;
  window.location.href = `/mybooklist/${userId}`;
});

// Search functionality with pagination
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

      // Calculate total pages
      totalPages = Math.ceil(data.total / 5);
      
      // Display results
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

              try {
                  const response = await fetch(`/api/user/${userId}/add-book`, {
                      method: 'POST',
                      headers: {
                          'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                          isbn: book.ISBN,
                          rating: selectedRating,
                          title: book["Book-Title"],
                          author: book["Book-Author"],
                          image: book["Image-URL-M"]
                      })
                  });

                  const result = await response.json();
                if (result.success) {
                    alert(`Book added successfully!`);
                    userAddedISBNs.push(book.ISBN);
                    addBtn.style.display = 'none';
                    select.style.display = 'none';
                    markAsAdded(ratingSection);
                }
                else {
                      alert(`Failed to add book: ${result.message || 'Unknown error'}`);
                  }
              } catch (error) {
                  console.error('Error adding book:', error);
                  alert('An error occurred while adding the book.');
              }
          });

          ratingSection.appendChild(select);
          ratingSection.appendChild(addBtn);
          bookInfo.appendChild(ratingSection);
          item.appendChild(bookInfo);
          resultsDiv.appendChild(item);
      });

      // Update pagination controls
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