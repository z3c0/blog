# Scraping Websites with Python

## Part 1: Getting to know your target

Before you begin coding, it's important you gather as much information about the target website as reasonably possible. This will prevent you from getting caught by an unforeseen pitfall later on.

If you want to skip straight to the coding, check back later for the next entry in this series.

To begin, start by seeking to understand as much as you can about the structure of the site, as well as your goals. Here's a couple of questions that you could start with:

1) What data am I trying to gather?

1) Is this site the primary source for that data? If not, do they specify their source? Repeat this line of questioning until you've discovered the "truest" source of the data (on the web, at least.)

1) Does the site allow anonymous access, or must you use a login?

1) How does the website organize the data?

### Interpreting the HTML

To begin, select a page that you would like to scrape data from. In this case, we'll be starting [here](https://www.metal-archives.com/lists/A).

```txt
https://www.metal-archives.com/lists/A
```

Right away, we can see the data we're targeting.

[pic-1](scraping_metallum-0-1.png)

There are a couple of other important details that are immediately apparent:

1) The header "Browse Bands - Alphabetically - A" should clue us in that we are only looking at a subset of the dataset - the bands beginning wiht "A", in particular.

1) The URL appears to denote which bands we are looking at.

    metal-archives.com/lists/**A**

1) There is a header above the page's data specifying the other options that can be fed to the same position as the "A" in the URL.

1) Below the header detailing the other list options, we can see a sub-header specifying the number of pages in the currently selected list. As of writing this post, there are 12,589 entries. Only the first 500 are visible currently.

On that final point, we've identified our next few steps.

1) Firstly, we need to find out how to grab the records from the page we're currently on.

1) After that, we will need to scrape the remaining records from the "A" list.

1) Once we've done that, we need to query the remaining lists, wherein we'll repeat steps 1 & 2.

Let's begin, shall we?

#### Getting data from the current page

Start by opening your browsers' developer tools (press F12). Navigate to the HTML inspector.

Once in the inspector, toggle the element picker tool on (usually located to the top left.) From there, select an element containing any of the data that you hope to obtain.
