#!/usr/bin/env python2
import ConfigParser
import getpass

CONFIG_FILE = None
MAX_COUNT = 1
DEBUG = False


def read_app_credentials(filename="app_credentials.cfg"):
    creds = ConfigParser.RawConfigParser()
    creds.read(filename)
    return creds


def read_config_file(filename=None):
    """Read and parse the configuration file, returning it as a ConfigParser
       object."""
    global CONFIG_FILE

    config = ConfigParser.RawConfigParser()

    if filename is None:
        filename = CONFIG_FILE

    config.read(filename)
    CONFIG_FILE = filename

    return config


def write_config_file(config):
    """Writes the configuration object to the previously-read config file."""
    global CONFIG_FILE

    if CONFIG_FILE is None:
        raise RuntimeError('CONFIG_FILE is None')

    with open(CONFIG_FILE, 'w') as fp:
        config.write(fp)


def get_mastodon(credentials, config):
    """Returns a Mastodon connection object."""
    from mastodon import Mastodon

    if not credentials.has_section('mastodon'):
        raise RuntimeError("no [mastodon] section in app credentials")

    for key in ['client_key', 'client_secret', 'instance']:
        if not credentials.has_option('mastodon', key):
            raise RuntimeError("no %s key in app credentials" % key)

    if not config.has_section('mastodon'):
        config.add_section('mastodon')
        write_config_file(config)

    # Log in
    if not config.has_option('mastodon', 'access_token'):
        mastodon = Mastodon(
                    client_id=credentials.get('mastodon', 'client_key'),
                    client_secret=credentials.get('mastodon', 'client_secret'),
                    api_base_url=credentials.get('mastodon', 'instance'))
        print("Logging into %s..." % credentials.get('mastodon', 'instance'))
        username = raw_input('E-mail address: ')
        password = getpass.getpass('Password: ')
        access_token = mastodon.log_in(username, password)
        config.set('mastodon', 'access_token', access_token)
        write_config_file(config)

    return Mastodon(
            client_id=credentials.get('mastodon', 'client_key'),
            client_secret=credentials.get('mastodon', 'client_secret'),
            api_base_url=credentials.get('mastodon', 'instance'),
            access_token=config.get('mastodon', 'access_token'))


def get_lastfm(credentials, config):
    import pylast

    if not credentials.has_section('lastfm'):
        raise RuntimeError("no [lastfm] section in app credentials")

    for key in ['api_key', 'shared_secret']:
        if not credentials.has_option('lastfm', key):
            raise RuntimeError("no %s key in app credentials" % key)

    if not config.has_section('lastfm'):
        config.add_section('lastfm')
        write_config_file(config)

    return pylast.LastFMNetwork(
        api_key=credentials.get('lastfm', 'api_key'),
        api_secret=credentials.get('lastfm', 'shared_secret'))


def set_lastfm_high_water_mark(config, last):
    """Set the marker for the latest last.fm track processed."""
    if not config.has_section('lastfm'):
        config.add_section('lastfm')

    config.set('lastfm', 'last_timestamp', last)
    write_config_file(config)


def get_lastfm_high_water_mark(config):
    """Get the marker for the latest last.fm track processed."""
    if (not config.has_section('lastfm')
        or not config.has_option('lastfm', 'last_timestamp')):
            return 1

    return config.getint('lastfm', 'last_timestamp')


def main():
    creds = read_app_credentials()
    cfg = read_config_file('config.cfg')

    masto = get_mastodon(creds, cfg)

    lastfm = get_lastfm(creds, cfg)
    lfmu = lastfm.get_user(cfg.get('lastfm', 'user'))

    last_ts = get_lastfm_high_water_mark(cfg)

    # iterate over tracks
    countdown = MAX_COUNT

    for p in reversed(lfmu.get_recent_tracks(time_from=last_ts, cacheable=False)):
        p_ts = int(p.timestamp)

        if DEBUG: print(p_ts, last_ts)
        if p_ts <= last_ts:
            continue

        if DEBUG: print p

        last_ts = p_ts
        t = p.track

        t_url = t.get_url()
        t_artist = t.get_artist()
        t_artist_name = t_artist.get_name() if t_artist is not None else "?"
        t_track_name = t.get_title()

        msg = "#nowplaying in Rey's Den\n\n%s - \"%s\"\n\n#np %s" % (t_artist_name, t_track_name, t_url)

        masto.status_post(msg, visibility = 'unlisted')
        countdown -= 1
        if countdown <= 0:
            break

    set_lastfm_high_water_mark(cfg, last_ts)


if __name__ == '__main__': main()

