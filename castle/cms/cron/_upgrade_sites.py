import argparse

import transaction
from AccessControl.SecurityManagement import newSecurityManager
from castle.cms.cron.utils import setup_site
from castle.cms.utils import retriable
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot


parser = argparse.ArgumentParser(
    description='...')
parser.add_argument('--site-id', dest='site_id', default=None)
parser.add_argument('--skip-incomplete', dest='skip_incomplete', default=False,
                    action='store_true')
args, _ = parser.parse_known_args()


@retriable(sync=True)
def upgrade(site):
    setup_site(site)

    # attempt to upgrade plone first
    pm = site.portal_migration
    report = pm.upgrade(dry_run=False)
    print(report)

    ps = site.portal_setup
    # go through all profiles that need upgrading
    for profile_id in ps.listProfilesWithUpgrades():
        # do our best to detect good upgrades
        if profile_id.split(':')[0] in (
                'Products.CMFPlacefulWorkflow', 'plone.app.iterate',
                'plone.app.multilingual', 'Products.PloneKeywordManager',
                'collective.easyform', 'plone.session'):
            continue
        if not profile_id.endswith(':default'):
            continue
        steps_to_run = ps.listUpgrades(profile_id)
        if steps_to_run:
            print('Running profile upgrades for {}'.format(profile_id))
            ps.upgradeProfile(profile_id)

        remaining = ps.listUpgrades(profile_id)
        if remaining:
            if args.skip_incomplete:
                print(
                    '[{}] Running upgrades did not finish all upgrade steps: {}'.format(
                        profile_id, remaining))
            else:
                raise Exception(
                    '[{}] Running upgrades did not finish all upgrade steps: {}'.format(
                        profile_id, remaining))

    transaction.commit()


def run(app):
    user = app.acl_users.getUser('admin')
    newSecurityManager(None, user.__of__(app.acl_users))

    if args.site_id:
        upgrade(app[args.site_id])
    else:
        for oid in app.objectIds():
            obj = app[oid]
            if IPloneSiteRoot.providedBy(obj):
                upgrade(obj)


if __name__ == '__main__':
    run(app)  # noqa
