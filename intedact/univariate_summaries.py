import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
import numpy as np
from collections import Counter
import seaborn as sns
from itertools import combinations
from matplotlib import gridspec
from IPython.display import display
from typing import Union, List, Tuple
from .plot_utils import *
from .data_utils import trim_values, compute_time_deltas, convert_to_freq_string
from .univariate_plots import (
    histogram,
    boxplot,
    countplot,
    time_series_countplot,
    plot_ngrams,
)
from .bivariate_plots import time_series_plot
from .config import TIME_UNITS
import calendar

FLIP_LEVEL_MINIMUM = 5


def compute_univariate_summary_table(
    data: pd.DataFrame, column: str, data_type: str, lower_trim=0, upper_trim=0
) -> pd.DataFrame:
    """
    Computes summary statistics for a numerical pandas DataFrame column.

    Computed statistics include:

      - mean and median
      - min and max
      - 25% percentile
      - 75% percentile
      - standard deviation and interquartile range
      - count and percentage of missing values

    Args:
        data: The dataframe with the column to summarize
        column: The column in the dataframe to summarize
        data_type: Type of column to use to determine summary values to return
        lower_trim: Number of values to trim from lower end of distribution
        upper_trim: Number of values to trim from upper end of distribution

    Returns:
        pandas DataFrame with one row containing the summary statistics for the provided column
    """
    data = trim_values(data, column, lower_trim, upper_trim)

    # Get summary table
    count_missing = data[column].isnull().sum()
    perc_missing = 100 * count_missing / data.shape[0]
    count_obs = data.shape[0] - count_missing
    count_levels = data[column].nunique()
    counts_table = pd.DataFrame(
        {
            "count_observed": [count_obs],
            "count_unique": [count_levels],
            "count_missing": [count_missing],
            "percent_missing": [perc_missing],
        },
        index=[column],
    )

    if data_type == "datetime":
        counts_table["min"] = data[column].min()
        counts_table["25%"] = data[column].quantile(0.25)
        counts_table["median"] = data[column].median()
        counts_table["75%"] = data[column].quantile(0.75)
        counts_table["max"] = data[column].max()
        counts_table["iqr"] = data[column].quantile(0.75) - data[column].quantile(0.25)
        return counts_table
    elif data_type == "continuous" or data_type == "datetime":
        stats_table = pd.DataFrame(data[column].describe()).T
        stats_table["iqr"] = data[column].quantile(0.75) - data[column].quantile(0.25)
        stats_table = stats_table[
            ["min", "25%", "50%", "mean", "75%", "max", "std", "iqr"]
        ]
        stats_table = stats_table.rename({"50%": "median"}, axis="columns")
        return pd.concat([counts_table, stats_table], axis=1)
    else:
        return counts_table


def discrete_univariate_summary(
    data: pd.DataFrame,
    column: str,
    fig_height: int = 5,
    fig_width: int = 10,
    fontsize: int = 15,
    color_palette: str = None,
    order: Union[str, List] = "auto",
    max_levels: int = 30,
    label_rotation: Optional[int] = None,
    label_fontsize: Optional[float] = None,
    flip_axis: Optional[bool] = None,
    percent_axis: bool = True,
    label_counts: bool = True,
    include_missing: bool = False,
    interactive: bool = False,
) -> Tuple[pd.DataFrame, plt.Figure]:
    """
    Creates a univariate EDA summary for a provided discrete data column in a pandas DataFrame.

    Summary consists of a count plot with twin axes for counts and percentages for each level of the
    variable and a small summary table.

    Args:
        data: pandas DataFrame with data to be plotted
        column: column in the dataframe to plot
        fig_width: figure width in inches
        fig_height: figure height in inches
        fontsize: Font size of axis and tick labels
        color_palette: Seaborn color palette to use
        order: Order in which to sort the levels of the variable for plotting:

         - **'auto'**: sorts ordinal variables by provided ordering, nominal variables by descending frequency, and numeric variables in sorted order.
         - **'descending'**: sorts in descending frequency.
         - **'ascending'**: sorts in ascending frequency.
         - **'sorted'**: sorts according to sorted order of the levels themselves.
         - **'random'**: produces a random order. Useful if there are too many levels for one plot.
         Or you can pass a list of level names in directly for your own custom order.
        max_levels: Maximum number of levels to attempt to plot on a single plot. If exceeded, only the
         max_level - 1 levels will be plotted and the remainder will be grouped into an 'Other' category.
        percent_axis: Whether to add a twin y axis with percentages
        label_counts: Whether to add exact counts and percentages as text annotations on each bar in the plot.
        label_fontsize: Size of the annotations text. Default tries to infer a reasonable size based on the figure
         size and number of levels.
        flip_axis: Whether to flip the plot so labels are on y axis. Useful for long level names or lots of levels.
         Default tries to infer based on number of levels and label_rotation value.
        label_rotation: Amount to rotate level labels. Useful for long level names or lots of levels.
        include_missing: Whether to include missing values as an additional level in the data
        interactive: Whether to display plot and table for interactive use in a jupyter notebook

    Returns:
        Summary table and matplotlib figure with countplot

    Example:
        .. plot::

            import seaborn as sns
            import intedact
            data = sns.load_dataset('tips')
            intedact.discrete_univariate_summary(data, 'day', interactive=True)
    """
    data = data.copy()
    if flip_axis is None:
        flip_axis = data[column].nunique() > FLIP_LEVEL_MINIMUM

    if color_palette != "":
        sns.set_palette(color_palette)
    else:
        sns.set_palette("tab10")

    # Get summary table
    summary_table = compute_univariate_summary_table(data, column, "discrete")

    # Plot countplot
    fig, axs = plt.subplots(1, 1, figsize=(fig_width, fig_height))
    ax = countplot(
        data,
        column,
        order=order,
        max_levels=max_levels,
        percent_axis=percent_axis,
        label_counts=label_counts,
        flip_axis=flip_axis,
        label_fontsize=label_fontsize,
        include_missing=include_missing,
        label_rotation=label_rotation,
        fontsize=fontsize,
    )

    if interactive:
        display(summary_table)
        plt.show()

    return summary_table, fig


def continuous_univariate_summary(
    data: pd.DataFrame,
    column: str,
    fig_height: int = 4,
    fig_width: int = 8,
    fontsize: int = 15,
    color_palette: str = None,
    bins: Optional[int] = None,
    transform: str = "identity",
    clip: float = 0,
    kde: bool = False,
    lower_trim: int = 0,
    upper_trim: int = 0,
    interactive: bool = False,
) -> None:
    """
    Creates a univariate EDA summary for a provided continuous data column in a pandas DataFrame.

    Summary consists of a histogram, boxplot, and small table of summary statistics.

    Args:
        data: pandas DataFrame to perform EDA on
        column: A string matching a column in the data to visualize
        fig_height: Height of the plot in inches
        fig_width: Width of the plot in inches
        fontsize: Font size of axis and tick labels
        color_palette: Seaborn color palette to use
        bins: Number of bins to use for the histogram. Default is to determines # of bins from the data
        transform: Transformation to apply to the data for plotting:

            - 'identity': no transformation
            - 'log': apply a logarithmic transformation with small constant added in case of zero values
            - 'log_exclude0': apply a logarithmic transformation with zero values removed
            - 'sqrt': apply a square root transformation
        kde: Whether to overlay a KDE plot on the histogram
        lower_trim: Number of values to trim from lower end of distribution
        upper_trim: Number of values to trim from upper end of distribution
        interactive: Whether to modify to be used with interactive for ipywidgets

    Returns:
        Tuple containing matplotlib Figure drawn and summary stats DataFrame

    Example:
        .. plot::

            import seaborn as sns
            import intedact
            data = sns.load_dataset('tips')
            intedact.continuous_univariate_summary(data, 'total_bill', interactive=True)[0]
    """
    data = data.copy()

    if color_palette != "":
        sns.set_palette(color_palette)
    else:
        sns.set_palette("tab10")

    # Get summary table
    table = compute_univariate_summary_table(
        data, column, "continuous", lower_trim, upper_trim
    )

    f, axs = plt.subplots(2, 1, figsize=(fig_width, fig_height * 2))
    histogram(
        data,
        column,
        ax=axs[0],
        bins=bins,
        transform=transform,
        clip=clip,
        lower_trim=lower_trim,
        upper_trim=upper_trim,
        kde=kde,
    )
    axs[0].set_xlabel("")
    boxplot(
        data,
        column,
        ax=axs[1],
        transform=transform,
        lower_trim=lower_trim,
        upper_trim=upper_trim,
    )
    set_fontsize(axs[0], fontsize)
    set_fontsize(axs[1], fontsize)

    if interactive:
        display(table)
        plt.show()

    return table, f


def datetime_univariate_summary(
    data: pd.DataFrame,
    column: str,
    fig_height: int = 4,
    fig_width: int = 8,
    fontsize: int = 15,
    color_palette: str = None,
    ts_freq: str = "auto",
    delta_units: str = "auto",
    ts_type: str = "line",
    trend_line: str = "auto",
    date_labels: Optional[str] = None,
    date_breaks: Optional[str] = None,
    lower_trim: int = 0,
    upper_trim: int = 0,
    interactive: bool = False,
) -> plt.Figure:
    """
    Creates a univariate EDA summary for a provided datetime data column in a pandas DataFrame.

    Produces the following summary plots:

      - a time series plot of counts aggregated at the temporal resolution provided by ts_freq
      - a time series plot of time deltas between successive observations in units defined by delta_freq
      - countplots for the following metadata from the datetime object:

        - day of week
        - day of month
        - month
        - year
        - hour
        - minute

    Args:
        data: pandas DataFrame to perform EDA on
        column: A string matching a column in the data
        fig_height: Height of the plot in inches
        fig_width: Width of the plot in inches
        fontsize: Font size of axis and tick labels
        color_palette: Seaborn color palette to use
        ts_freq: String describing the frequency at which to aggregate data in one of two formats:

            - A `pandas offset string <https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects>`_.
            - A human readable string in the same format passed to date breaks (e.g. "4 months")
            Default is to attempt to intelligently determine a good aggregation frequency.
        delta_units: String describing the units in which to compute time deltas between successive observations in one of two formats:

            - A `pandas offset string <https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects>`_.
            - A human readable string in the same format passed to date breaks (e.g. "4 months")
            Default is to attempt to intelligently determine a good frequency unit.
        ts_type: 'line' plots a line graph while 'point' plots points for observations
        trend_line: Trend line to plot over data. "None" produces no trend line. Other options are passed
            to `geom_smooth <https://plotnine.readthedocs.io/en/stable/generated/plotnine.geoms.geom_smooth.html>`_.
        date_labels: strftime date formatting string that will be used to set the format of the x axis tick labels
        date_breaks: Date breaks string in form '{interval} {period}'. Interval must be an integer and period must be
          a time period ranging from seconds to years. (e.g. '1 year', '3 minutes')
        lower_trim: Number of values to trim from lower end of distribution
        upper_trim: Number of values to trim from upper end of distribution
        span: Span parameter to determine amount of smoothing for loess trend line
        interactive: Whether to display figures and tables in jupyter notebook for interactive use

    Returns:
        matplotlib Figure plot is drawn to

    Examples:
        .. plot::

            import pandas as pd
            import intedact
            data = pd.read_csv("https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/tidytuesday_tweets/data.csv")
            data['created_at'] = pd.to_datetime(data.created_at)
            intedact.datetime_univariate_summary(data, 'created_at', ts_freq='1 week', delta_freq='1 hour')
    """
    data = data.copy()
    data = trim_values(data, column, lower_trim, upper_trim)

    if trend_line == "none":
        trend_line = None
    if date_breaks == "auto":
        date_breaks = None
    if date_labels == "auto":
        date_labels = None

    if color_palette != "":
        sns.set_palette(color_palette)
    else:
        sns.set_palette("tab10")

    # Compute extra columns with datetime attributes
    data["Month"] = data[column].dt.month_name()
    data["Day of Month"] = data[column].dt.day
    data["Year"] = data[column].dt.year
    data["Hour"] = data[column].dt.hour
    data["Day of Week"] = data[column].dt.day_name()

    # Compute time deltas
    data["deltas"], delta_units = compute_time_deltas(data[column], delta_units)

    # Compute summary table
    table = compute_univariate_summary_table(data, column, "datetime")
    delta_table = compute_univariate_summary_table(
        data.iloc[1:, :], "deltas", "continuous"
    )
    delta_table.index = [f"Time Deltas ({delta_units})"]
    table = pd.concat([table, delta_table], axis=0)
    if interactive:
        display(table)

    fig = plt.figure(figsize=(fig_width, fig_height * 4))
    spec = gridspec.GridSpec(ncols=2, nrows=5, figure=fig)

    # time series count plot
    ax = fig.add_subplot(spec[0, :])
    ax = time_series_countplot(
        data,
        column,
        ax,
        ts_freq=ts_freq,
        ts_type=ts_type,
        trend_line=trend_line,
        date_breaks=date_breaks,
        date_labels=date_labels,
    )
    set_fontsize(ax, fontsize)

    # Summary plots of time deltas
    ax = fig.add_subplot(spec[1, 0])
    ax = histogram(data, "deltas", ax=ax)
    ax.set_xlabel(f"{delta_units.title()} between observations")
    set_fontsize(ax, fontsize)

    ax = fig.add_subplot(spec[1, 1])
    ax = boxplot(data, "deltas", ax=ax)
    ax.set_xlabel(f"{delta_units.title()} between observations")
    set_fontsize(ax, fontsize)

    # countplot by month
    data["Month"] = pd.Categorical(
        data["Month"], categories=list(calendar.month_name)[1:], ordered=True
    )
    ax = fig.add_subplot(spec[2, 0])
    ax = countplot(
        data,
        "Month",
        ax,
        label_fontsize=10,
        flip_axis=True,
        fontsize=fontsize,
    )

    # countplot by day of month
    data["Day of Month"] = pd.Categorical(
        data["Day of Month"], categories=np.arange(1, 32, 1), ordered=True
    )
    ax = fig.add_subplot(spec[2, 1])
    ax = countplot(
        data,
        "Day of Month",
        ax,
        label_counts=False,
        flip_axis=True,
        max_levels=35,
        fontsize=fontsize,
    )
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=9)

    # countplot by day of week
    data["Day of Week"] = pd.Categorical(
        data["Day of Week"], categories=list(calendar.day_name), ordered=True
    )
    ax = fig.add_subplot(spec[3, 0])
    ax = countplot(
        data,
        "Day of Week",
        ax,
        label_fontsize=10,
        flip_axis=True,
        fontsize=fontsize,
    )

    # countplot by hour of day
    data["Hour"] = pd.Categorical(
        data["Hour"], categories=np.arange(0, 24, 1), ordered=True
    )
    ax = fig.add_subplot(spec[3, 1])
    ax = countplot(
        data, "Hour", ax, label_counts=False, flip_axis=True, fontsize=fontsize
    )
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=9)

    plt.tight_layout()
    if interactive:
        plt.show()

    return table, fig


def text_univariate_summary(
    data,
    column,
    fig_height=6,
    fig_width=18,
    fontsize: int = 15,
    color_palette: Optional[str] = None,
    top_ngrams=10,
    compute_ngrams=False,
    remove_punct=True,
    remove_stop=True,
    lower_case=True,
    interactive=False,
):
    """
    Creates a univariate EDA summary for a provided text variable column in a pandas DataFrame.

    For the provided column produces:
      - histograms of token and character counts across entries
      - boxplot of document frequencies
      - countplots with top_ngrams unigrams, bigrams, and trigrams
      - title with total # of tokens, vocab size, and corpus size

    Args:
        data: Dataset to perform EDA on
        column: A string matching a column in the data
        fig_height: Height of the plot
        fig_width: int, optional
        Width of the plot
    top_ngrams: int, optional
        Maximum number of ngrams to plot for the top most frequent unigrams and bigrams
    hist_bins: int, optional (Default is 0 which translates to automatically determined bins)
        Number of bins to use for the histograms
    transform: str, ['identity', 'log', 'log_exclude0']
        Transformation to apply to the histogram/boxplot variables for plotting:
          - 'identity': no transformation
          - 'log': apply a logarithmic transformation with small constant added in case of 0
          - 'log_exclude0': apply a logarithmic transformation with zero removed
    lower_quantile: float, optional [0, 1]
        Lower quantile of data to remove before plotting histogram/boxplots for ignoring outliers
    upper_quantile: float, optional [0, 1]
        Upper quantile of data to remove before plotting histograms/boxplots for ignoring outliers
    remove_stop: bool, optional
        Whether to remove stop words from consideration for ngrams
    remove_punct: bool, optional
        Whether to remove punctuation from consideration for ngrams
    lower_case: bool, optional
        Whether to lower case text when forming tokens for ngrams

    Returns
    -------
    None
        No return value. Directly displays the resulting matplotlib figure and table.
    """
    from nltk import word_tokenize
    from nltk.corpus import stopwords

    if color_palette != "":
        sns.set_palette(color_palette)
    else:
        sns.set_palette("tab10")

    data = data.copy()
    data = data.dropna(subset=[column])

    # Compute number of characters per document
    data["# Characters / Document"] = data[column].apply(lambda x: len(x))

    # Tokenize the text
    data["tokens"] = data[column].apply(lambda x: [w for w in word_tokenize(x)])
    if lower_case:
        data["tokens"] = data["tokens"].apply(lambda x: [w.lower() for w in x])
    if remove_stop:
        stop_words = set(stopwords.words("english"))
        data["tokens"] = data["tokens"].apply(
            lambda x: [w for w in x if w.lower() not in stop_words]
        )
    if remove_punct:
        data["tokens"] = data["tokens"].apply(lambda x: [w for w in x if w.isalnum()])
    data["# Tokens / Document"] = data["tokens"].apply(lambda x: len(x))

    # Compute summary table
    table = compute_univariate_summary_table(data, column, "discrete")
    table["vocab_size"] = len(set([x for y in data["tokens"] for x in y]))
    tokens_table = compute_univariate_summary_table(
        data, "# Tokens / Document", "continuous"
    )
    char_table = compute_univariate_summary_table(
        data, "# Characters / Document", "continuous"
    )
    table = pd.concat([table, tokens_table, char_table], axis=0)
    if interactive:
        display(table)

    if compute_ngrams:
        fig = plt.figure(figsize=(fig_width, fig_height * 3))
        spec = gridspec.GridSpec(ncols=2, nrows=3, figure=fig)
        num_docs = data.shape[0]

        ax = fig.add_subplot(spec[0, 0])
        ax = plot_ngrams(
            data["tokens"], num_docs, ngram_type="tokens", lim_ngrams=top_ngrams, ax=ax
        )

        ax = fig.add_subplot(spec[1, 0])
        ax = plot_ngrams(
            data["tokens"], num_docs, ngram_type="bigrams", lim_ngrams=top_ngrams, ax=ax
        )

        ax = fig.add_subplot(spec[2, 0])
        ax = plot_ngrams(
            data["tokens"],
            num_docs,
            ngram_type="trigrams",
            lim_ngrams=top_ngrams,
            ax=ax,
        )

    else:
        fig = plt.figure(figsize=(fig_width, fig_height))
        spec = gridspec.GridSpec(ncols=3, nrows=1, figure=fig)

    # histogram of tokens characters per document
    ax = fig.add_subplot(spec[0, 1] if compute_ngrams else spec[0, 0])
    ax = histogram(data, "# Tokens / Document", ax=ax)

    # histogram of tokens characters per document
    ax = fig.add_subplot(spec[1, 1] if compute_ngrams else spec[0, 1])
    ax = histogram(data, "# Characters / Document", ax=ax)

    # histogram of tokens characters per document
    ax = fig.add_subplot(spec[2, 1] if compute_ngrams else spec[0, 2])
    tmp = pd.DataFrame({"# Obs / Document": list(data[column].value_counts())})
    ax = boxplot(tmp, "# Obs / Document", ax=ax)

    plt.tight_layout()
    if interactive:
        plt.show()
    return fig


def list_univariate_eda(data, column, fig_height=4, fig_width=8, top_entries=10):
    """
    Creates a univariate EDA summary for a provided list column in a pandas DataFrame.

    The provided column should be an object type containing lists, tuples, or sets.

    Parameters
    ----------
    data: pandas.DataFrame
        Dataset to perform EDA on
    column: str
        A string matching a column in the data
    fig_height: int, optional
        Height of the plot
    fig_width: int, optional
        Width of the plot
    top_entries: int, optional
        Maximum number of entries to plot for the top most frequent single entries and pairs.

    Returns
    -------
    None
        No return value. Directly displays the resulting matplotlib figure.
    """
    data = data.copy()
    # handle missing data
    num_missing = data[column].isnull().sum()
    perc_missing = num_missing / data.shape[0]
    data.dropna(subset=[column], inplace=True)

    fig = (ggplot() + geom_blank(data=data) + theme_void()).draw()
    fig.set_size_inches(fig_width, fig_height * 3)
    gs = gridspec.GridSpec(3, 2)

    # plot most common entries
    ax_single = fig.add_subplot(gs[0, :])
    entries = [i for e in data[column] for i in e]
    singletons = pd.DataFrame({"single": entries})
    order = list(
        singletons["single"].value_counts().sort_values(ascending=False).index
    )[:top_entries][::-1]
    singletons["single"] = pd.Categorical(singletons["single"], order)
    singletons = singletons.dropna()

    gg_s = (
        ggplot(singletons, aes(x="single"))
        + geom_bar(fill=BAR_COLOR, color="black")
        + coord_flip()
    )
    _ = gg_s._draw_using_figure(fig, [ax_single])
    ax_single.set_ylabel("Most Common Entries")
    add_percent_axis(ax_single, data.shape[0], flip_axis=True)

    # plot most common entries
    ax_double = fig.add_subplot(gs[1, :])
    pairs = [comb for coll in data[column] for comb in combinations(coll, 2)]
    pairs = pd.DataFrame({"pair": pairs})
    order = list(pairs["pair"].value_counts().sort_values(ascending=False).index)[
        :top_entries
    ][::-1]
    pairs["pair"] = pd.Categorical(pairs["pair"], order)
    pairs = pairs.dropna()

    gg_s = (
        ggplot(pairs, aes(x="pair"))
        + geom_bar(fill=BAR_COLOR, color="black")
        + coord_flip()
    )
    _ = gg_s._draw_using_figure(fig, [ax_double])
    ax_double.set_ylabel("Most Common Entry Pairs")
    ax_double.set_xlabel("# Observations")
    add_percent_axis(ax_double, data.shape[0], flip_axis=True)

    # plot number of elements
    data["num_entries"] = data[column].apply(lambda x: len(x))
    ax_num = fig.add_subplot(gs[2, 0])
    gg_hour = ggplot(data, aes(x="num_entries")) + geom_histogram(
        bins=data["num_entries"].max(), fill=BAR_COLOR, color="black"
    )
    _ = gg_hour._draw_using_figure(fig, [ax_num])
    ax_num.set_ylabel("count")
    ax_num.set_xlabel("# Entries / Observation")
    ax_num.set_xticks(np.arange(0, data["num_entries"].max() + 1))
    ax_num.set_xticklabels(np.arange(0, data["num_entries"].max() + 1))
    add_percent_axis(ax_num, data.shape[0], flip_axis=False)

    ax_obs = fig.add_subplot(gs[2, 1])
    tmp = pd.DataFrame({"obs": list(data[column].value_counts())})
    gg_box = (
        ggplot(tmp, aes(x=[""], y="obs"))
        + geom_boxplot(color="black", fill=BAR_COLOR)
        + coord_flip()
    )
    _ = gg_box._draw_using_figure(fig, [ax_obs])
    ax_obs.set_xlabel("# Observations / Unique List")

    ax_single.set_title(
        f"{len(set(entries))} unique entries with {len(entries)} total entries across {data[column].size} observations"
    )
    plt.show()
