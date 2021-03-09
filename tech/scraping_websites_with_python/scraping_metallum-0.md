# Scraping Websites with Python

## Part 1: Getting to know your target (Analysis)

Before you begin coding, it's important you gather as much information about the target website as reasonably possible. This will prevent you from getting caught by an unforeseen pitfall later on. For the purpose of this tutorial, we are going to be analyzing the popular music data site metal-archives.com, known for it's extensive data on metal bands.

If you want to skip straight to the coding, check back later for the next entry in this series.

To begin, start by seeking to understand as much as you can about the structure of the site. This will help to more clearly lay out your goals. Here's a couple of questions that you could start with:

1) What data am I trying to gather?

1) Is this site the primary source for that data? If not, do they specify their source? Repeat this line of questioning until you've discovered the "truest" source of the data (on the web, at least.)

1) Does the site allow anonymous access, or must you use a login?

1) How does the website organize the data?

### Analyzing the Website

To begin, select a page that you would like to scrape data from. In this case, we'll be starting [here](https://www.metal-archives.com/lists/A).

```txt
https://www.metal-archives.com/lists/A
```

Right away, we can see the data we're targeting.

![Encyclopaedia Metallum A Bands List](https://raw.githubusercontent.com/z3c0/blog/main/tech/scraping_websites_with_python/scraping_metallum-0-1.PNG)

There are a couple of other important details that are immediately apparent:

1) The header "Browse Bands - Alphabetically - A" should clue us in that we are only looking at a subset of the dataset - the bands beginning with "A", in particular.

1) The URL appears to denote which bands we are looking at.

    metal-archives.com/lists/**A**

1) There is a navigation bar above the page's data specifying the other options that can be fed to the same position as the "A" in the URL.

1) Below the header detailing the other list options, we can see a sub-header specifying the number of pages in the currently selected list. As of writing this post, there are 12,589 entries. Only the first 500 records are visible currently.

1) Depending on your internet speed, you may have noticed a slight delay in the list of bands loads. This implies that the content is being dynamically-rendered after page load.

    - If you didn't catch this, try throttling your speed from the Network tools in your browser's developer tools (press F12).

On that final point, we've identified our next few steps.

***

**Step 1**: Firstly, we need to find out how to grab the records from the page we're currently on.

**Step 2**: After that, we will need to scrape the remaining records from the "A" list.

**Step 3**: Once we've done that, we need to query the remaining lists, wherein we'll repeat Steps 1 & 2.

***

### Getting Data from the Current Page

The dynamic rendering that we noticed earlier indicates that we'll need to start by checking what requests our target is making after page load. You can do this by  opening your browser's developer tools (press F12) and navigating to the Network page.

Once there, set your throttling speed to DSL and refresh the page.

For the first second or two, you should see an empty list.

![Empty A Bands List](https://raw.githubusercontent.com/z3c0/blog/main/tech/scraping_websites_with_python/scraping_metallum-0-2.PNG)

After that, you should see a flurry of requests popping up in the Network tab. This is the page loading its content. As of writing this, loading the page with a fresh cache results in around twenty different web requests. The next step would be to identify which of those requests was for our target dataset.

![A Bands Web Requests](https://raw.githubusercontent.com/z3c0/blog/main/tech/scraping_websites_with_python/scraping_metallum-0-3.PNG)

Let's start by filtering out results that we know are irrelevant. The best way to do this would be to utilize the filetype filters at the top of the table (*All*, *HTML*, *CSS*, *JS*, etc). To limit the results to web requests fetching data, select the filter for *XHR*. XHR stands for [XML HTTP Request](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest), which is the standard method that web pages use for dynamically loading content.

After filtering the results, you should be left with a single JSON request. A quick glance at the Response text confirms that this is indeed the data we're looking for.

![A Bands JSON Response](https://raw.githubusercontent.com/z3c0/blog/main/tech/scraping_websites_with_python/scraping_metallum-0-4.PNG)

Let's look a little closer. Select the Headers tab.

![A Bands JSON Request Header](https://raw.githubusercontent.com/z3c0/blog/main/tech/scraping_websites_with_python/scraping_metallum-0-5.PNG)

Now we can see the actual URL for our data.

```txt
https://www.metal-archives.com/browse/ajax-letter/l/A/json/1?sEcho=1&iColumns=4&sColumns=&iDisplayStart=0&iDisplayLength=500&mDataProp_0=0&mDataProp_1=1&mDataProp_2=2&mDataProp_3=3&iSortCol_0=0&sSortDir_0=asc&iSortingCols=1&bSortable_0=true&bSortable_1=true&bSortable_2=true&bSortable_3=false&_=1615303200187
```

You may notice the excessive use of query string parameters - trying to reverse engineer each one's purpose can be a very tedious and daunting task. To make our lives easier, we're going to start removing each one until we've identified which parameters are actually required to retrieve the data. After removing the unnecessary parameters, you should be left with a much shorter URL.

```txt
https://www.metal-archives.com/browse/ajax-letter/l/A/json/1?sEcho=1&iDisplayStart=0&iDisplayLength=500
```

Directly visiting the URL should return a page of JSON data. JSON is extremely easy to interact with programmatically, so this is undoubtedly the best way for us to extract the data from the current page (**Step 1**). We can also see some values in the dataset that will come in handy for **Step 2** - specifically ```iTotalRecords```, which informs us of the overall size of the dataset. We will know that we've retrieved the entire dataset once we've obtained the amount of records specified by ```iTotalRecords```.

Now let's return to looking at our shortened URL. We can divide this URL into four important pieces.

1) The request endpoint ```/browse/ajax-letter/l/A/json/1```

    - Similar to before, we can see that the URL denotes that we're looking at the "A" list. This will come in handy later, when it's time to start getting data from the other lists (**Step 3**).

1) The ```sEcho``` parameter

    - This parameter is simple - passing a ```1``` to ```sEcho``` in the request results in an ```sEcho``` of ```1``` in the response. Passing a ```2``` results in a ```2```, and so on. This technique exists so that responses can be easily matched back to their corresponding request, in the event of many requests being made asynchronously. This could come in handy later.

1) The ```iDisplayStart``` parameter

    - This parameter is the offset of our dataset. When passing ```n``` value to this parameter, it instructs the API that we would like to fetch a subset of records beginning at the ```nth``` position of the overall dataset. This is going to be paramount in fetching all ~12,500 records (**Step 2**)

1) The ```iDisplayLength``` parameter

    - As you'd expect, this parameter is meant to be paired with ```iDisplayStart```, and specifies how many records to grab after the starting point. This will also come in handy for **Step 2**
    Currently, it's set to ```500```. If you pass the parameter ```1000```, you'll see that the query still only returns 500 records. This means that 500 records is a hard limit defined in the API. We are going to have to work within that limit.

At this point, we can say that we have enough information to start getting data from the current page (**Step 1**). However, thanks to our analysis, we have also gained an understanding of **Steps 2 & 3**. Let's revisit them with our new information.

***

**Step 1**: Grab the records from the page we're currently on.

We now know that this is done by sending a request to ```https://www.metal-archives.com/browse/ajax-letter/l/A/json/1?sEcho=1&iDisplayStart=0&iDisplayLength=500```

**Step 2**: Get the remaining records from the "A" list.

We can do this by changing the values in the ```iDisplayStart``` and ```iDisplayLength``` parameters, until ```iDisplayStart``` is greater than ```iTotalRecords```.

**Step 3**: Query the remaining lists

This can be done by parameterizing the letter within the URL ```/browse/ajax-letter/l/{RIGHT HERE}/json/1```. However, we still haven't confirmed which values can be successfully passed to that position. That is our next lead for analysis.

***

### Querying the Remaining Data

The only information left to gather before we can start coding is what values we can pass to the API endpoint to return the remaining lists. Given that our lists our organized alphabetically, we can logically reason that the remaining lists are retrieved by passing in the corresponding letter. This is easily confirmed by plugging in any letter and observing the results.

Requesting ```https://www.metal-archives.com/browse/ajax-letter/l/Z/json/1?sEcho=1&iDisplayStart=0&iDisplayLength=500``` returns the first 500 (or less) bands beginning with "Z", confirming our theory. But what of the bands that begin with a number or symbol?

The answer to our question can be found in the navigation bar we spotted on our first pass of the web page.

![Navigation Bar](https://raw.githubusercontent.com/z3c0/blog/main/tech/scraping_websites_with_python/scraping_metallum-0-6.PNG)

At the end of the bar, we can see two options: ```#``` and ```~```. Selecting each and examining the JSON response after page load turns up exactly the information we're looking for.

Selecting ```#``` sends a request to ```/browse/ajax-letter/l/NBR/json/1```, meaning that numeric names are denoted as ```NBR```.

Selecting ```~``` sends a request to ```/browse/ajax-letter/l/~/json/1```, meaning that symbolic names are denoted as ```~```.

With that, we can assemble our parameters needed to get every list:

```txt
A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, NBR, and ~
```

Our analysis is now complete.

***

### Finalizing the steps

Now that we have a complete picture of what it takes to retrieve our target dataset, we can redefine our steps to more resemble what our code will look like.

***

**Step 1**: Loop over the endpoint ```/browse/ajax-letter/l/{LETTER}/json/1?sEcho=1&iDisplayStart=0&iDisplayLength=500``` where ```LETTER``` is a value from
```[A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, NBR, ~]```

**Step 2**: At each iteration of **Step 1**, increment ```iDisplayStart``` by ```iDisplayLength``` until ```iDisplayStart``` is greater than ```iTotalRecords```, grabbing records from each endpoint.

***

We've now reduced our steps to only two, and those steps are in reverse order to how they appeared when we initially defined them. This is why it is important to finish your analysis before beginning to code - otherwise, you might have to do some major restructuring to your code to account for each new discovery.

Let's review some of what we learned.

1) We can't just scrape the HTML elements that are available at page load, due to the page dynamically loading content. We will instead need to utilize the website's API to retrieve our target dataset.

2) The dataset is segmented by two dimensions: 1) the letter the bands begin with and 2) the number of records returned. We will need to incrementally load our data across both dimensions to retrieve the entire dataset.

By thoroughly analyzing our target, we've greatly trimmed down the amount of time we're going to need to code a solution. We're now ready to start coding.
***

Check back in a week for the next installment: *Scraping the Data (using Requests, BeautifulSoup4, and Pandas)*
